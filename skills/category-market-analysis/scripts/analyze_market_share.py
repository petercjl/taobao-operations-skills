# -*- coding: utf-8 -*-
# ⚠ 快照来源：skills/category-market-insight/scripts/analyze_market_share.py（拆分迁移，2026-08-21）。
# 原件仍被 category-market-insight（迁移期单体）使用；修改本文件时必须评估是否需双向同步。
"""
计算品类市场占比、电商版 KANO 量化指标与「规则初判」。

核心原则（v1.1）：
- 脚本只算指标 + 给出 KANO「规则初判」（kano_initial_suggestion + kano_rule_hit）
- 最终 KANO 层由 SKILL.md Step 5.1 模型基于「初判 + 类目权威 + 卖点语义」做二次终判，
  并把 kano_final.json 中的 kano_layer 回灌到 market_share.json 各卖点

输入：
- top_items_raw.json（fetch_top_items.py 产出）
- item_attributes.json（模型基于品类属性词典提取）
- category_selling_point_strategy.json（可选；上游取数技能产出的类目决策属性契约）
- default_config.json（KANO 阈值预设、独特性阈值）

输出（写入分类见 write_guard.py）：
- market_share.json 属 `artifact`：目标已存在时必须 `--allow-overwrite 中间数据文件/market_share.json`
  精确授权，覆盖前自动备份到 `临时文件/write-backup-*/`；回灌模式对自身产物的设计内增量自授权。
- market_share.json 每个卖点扩展为：
    metrics{D_buyer_share, P_item_coverage, R_premium, H_head_support, E_price_premium, band_distribution}
    + category_authority{is_key_decision_attr, weight_rank, is_core_factor}
    + kano_initial_suggestion / kano_rule_hit / rule_match_detail
    + uniqueness_verdict
    + 兼容字段（item_count/item_share/pay_byr_cnt_min/pay_byr_cnt_share/top_concentration/head_item_ids/kano_layer）

口径：
- 商品个数占比分母 = top100 商品总数（动态算）
- 支付买家数占比分母 = 所有商品 pay_byr_cnt_min 累加（区间下界，毛估）
- 头部集中度 = 维度内 top N 的 pay_byr_cnt_min 累加 / 该维度全部 pay_byr_cnt_min
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import write_guard  # noqa: E402  写入分类 / 路径守卫 / 覆盖守卫


# --------- KANO 阈值预设（与 default_config.json 对齐，作为 fallback 兜底） ---------
DEFAULT_KANO_PRESETS: Dict[str, Dict[str, Dict[str, float]]] = {
    "default": {
        "R1": {"d_min": 0.50, "p_min": 0.60, "r_min": 0.85, "r_max": 1.15},
        "R2": {"d_min": 0.30, "p_min": 0.20, "p_max": 0.70, "r_min": 1.15, "h_min": 1.0},
        "R3": {"d_min": 0.08, "p_max": 0.20, "r_min": 1.50, "h_min": 1.30},
        # R4 无差异型（v1.2 收紧）：严格 AND（D ≤ d_max AND R ≤ r_max）+ 最小样本量保护
        # 移除原 d_p_ratio_max 兜底（容易误伤中等覆盖卖点），改为 item_count < min_item_count 时不判 R4
        "R4": {"d_max": 0.02, "r_max": 0.80, "min_item_count": 5},
    },
    "loose_excitement": {
        "R1": {"d_min": 0.50, "p_min": 0.60, "r_min": 0.85, "r_max": 1.15},
        "R2": {"d_min": 0.25, "p_min": 0.15, "p_max": 0.70, "r_min": 1.10, "h_min": 1.0},
        "R3": {"d_min": 0.05, "p_max": 0.25, "r_min": 1.30, "h_min": 1.15},
        # 兴奋型放宽时，无差异更严：D 上限再降一档，避免长尾卖点被错判
        "R4": {"d_max": 0.015, "r_max": 0.80, "min_item_count": 5},
    },
    "strict_basic": {
        "R1": {"d_min": 0.55, "p_min": 0.65, "r_min": 0.90, "r_max": 1.10},
        "R2": {"d_min": 0.30, "p_min": 0.20, "p_max": 0.65, "r_min": 1.20, "h_min": 1.05},
        "R3": {"d_min": 0.08, "p_max": 0.18, "r_min": 1.50, "h_min": 1.30},
        "R4": {"d_max": 0.02, "r_max": 0.80, "min_item_count": 5},
    },
}

DEFAULT_UNIQUENESS = {
    "unique_max_coverage": 0.10,
    "homogenized_min_coverage": 0.50,
}

# ⛔ 品牌类 pname 黑名单：仅过滤「产品所属品牌」语义
# 注意：「适配机型/适配品牌/兼容品牌」等 pname 虽然 vname 含品牌名，
#       但它们是配件类目的核心决策属性（如 "适配华为" 是充电宝的合法卖点），
#       禁止加入此黑名单。
BRAND_PNAME_BLACKLIST = {"品牌", "品牌名", "品牌类型", "brand"}


# --------- 通用工具 ---------
def safe_round(value: Optional[float], ndigits: int = 1) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


def safe_round_ratio(value: Optional[float], ndigits: int = 3) -> Optional[float]:
    """保留 3 位小数的比率（不乘以 100）。"""
    return safe_round(value, ndigits)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guarded_write_json(path: str, payload: Any, allow_overwrite: Sequence[str] = ()) -> Dict[str, Any]:
    """market_share.json 属 artifact：路径守卫 → 覆盖授权 → 备份 → .partial 原子替换。

    `中间数据文件/` 是编排方共享目录（下游报告技能正在消费），未获精确授权时拒绝覆盖，
    避免同一 work_dir 重跑静默改写已被消费的结论文件。
    """
    try:
        return write_guard.write_json(path, payload, artifact_type="artifact",
                                      label=os.path.basename(path),
                                      allow_overwrite=allow_overwrite)
    except write_guard.WriteGuardError as exc:
        print(f"[analyze_market_share] FAIL 写入被守卫拒绝: {exc}", file=sys.stderr)
        sys.exit(2)


def parse_band_midprice(band_label: Optional[str]) -> Optional[float]:
    """根据 band 字符串估算代理价（用于 E_price_premium）。
    - "0-135.0" → 67.5
    - "500以上" / "500+" → 500 × 1.5 = 750
    - 解析失败返回 None
    """
    if not band_label:
        return None
    s = str(band_label).strip().replace(" ", "")
    # 开口区间
    if s.endswith("以上") or s.endswith("+"):
        try:
            base = float(s.replace("以上", "").replace("+", ""))
            return base * 1.5
        except (TypeError, ValueError):
            return None
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2:
            try:
                lo = float(parts[0])
                hi = float(parts[1])
                return (lo + hi) / 2.0
            except (TypeError, ValueError):
                return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# --------- 输入加载 ---------
def load_attrs_map(path: str) -> Dict[str, Dict[str, Any]]:
    payload = load_json(path)
    items = payload.get("items") or []
    return {str(it.get("itemId")): it for it in items if it.get("itemId")}


def load_strategy_authority(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """加载 category_selling_point_strategy.json，按卖点名建立权威映射。

    同时兼容三种结构：
    1. v2 富结构（推荐，类目决策属性接口完整返回）：
       - {"consumer_decision_factors": {"search": {"data": {"result": [{"pname": ..., "v_list": [{"vname": ...}]}]}},
                                          "purchase": {...}},
          "selling_point_recommendations": {"core_selling_points": [{"name": ..., "weight": ...}]},
          "summary": {"top_decision_attributes": [{"attribute": ..., "top_values": [...]}]}}
    2. v1 简化结构（老版 args 调用或占位）：
       - {"selling_point_strategy": [{"selling_point": "快充", "weight_rank": 1, "is_core_factor": true}]}
    3. 更细粒度旧结构（历史兼容）：
       - {"key_decision_attrs": [...], "search_decision": [...], "purchase_decision": [...],
          "core_factors": [...], "non_core_factors": [...]}
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        payload = load_json(path)
    except Exception:
        return {}

    auth: Dict[str, Dict[str, Any]] = {}
    # 记录在哪些环节被提及（search / purchase），同时出现者设 is_core_factor=True
    factor_envs: Dict[str, set] = defaultdict(set)

    def _absorb(items: List[Any], default_core: Optional[bool] = None,
                 weight_hint: Optional[float] = None, env: Optional[str] = None) -> None:
        for idx, raw in enumerate(items or []):
            if isinstance(raw, str):
                name = raw
                rec: Dict[str, Any] = {"name": name}
            elif isinstance(raw, dict):
                rec = dict(raw)
                name = (rec.get("name") or rec.get("attr") or rec.get("attribute")
                        or rec.get("selling_point") or rec.get("vname") or rec.get("pname"))
            else:
                continue
            if not name:
                continue
            entry = auth.setdefault(name, {
                "is_key_decision_attr": False,
                "weight_rank": None,
                "is_core_factor": False,
            })
            entry["is_key_decision_attr"] = True
            # weight_rank：优先取显式字段，其次取下标+1
            wr = rec.get("weight_rank") or rec.get("rank") or (idx + 1)
            try:
                wr_int = int(wr)
                if entry["weight_rank"] is None or wr_int < entry["weight_rank"]:
                    entry["weight_rank"] = wr_int
            except (TypeError, ValueError):
                pass
            ic = rec.get("is_core_factor")
            if ic is None and default_core is not None:
                ic = default_core
            # weight_hint 阈值：权重 ≥ 0.7 视为 core
            w = rec.get("weight") or rec.get("std_score_v") or rec.get("score")
            try:
                w_float = float(w) if w is not None else None
            except (TypeError, ValueError):
                w_float = None
            if w_float is not None and w_float >= 0.7:
                ic = True
            if ic:
                entry["is_core_factor"] = True
            if env:
                factor_envs[name].add(env)

    if isinstance(payload, dict):
        # ----- v2 富结构：consumer_decision_factors.{search,purchase}.data.result[].v_list -----
        cdf = payload.get("consumer_decision_factors") or {}
        for env_key in ("search", "purchase"):
            env_block = cdf.get(env_key) or {}
            if not isinstance(env_block, dict):
                continue
            data = env_block.get("data") or {}
            result_list = data.get("result") if isinstance(data, dict) else None
            if not isinstance(result_list, list):
                continue
            for attr_block in result_list:
                if not isinstance(attr_block, dict):
                    continue
                # ⛔ 品牌类属性的 vname 不进卖点权威词表（品牌走独立 brand_share 维度）
                pname = (attr_block.get("pname") or attr_block.get("attribute") or "").strip()
                if pname.lower() in BRAND_PNAME_BLACKLIST:
                    continue
                v_list = attr_block.get("v_list") or []
                # v_list 中的 vname 才是真正可匹配的卖点关键词
                _absorb(v_list, env=env_key)

        # ----- v2 富结构：selling_point_recommendations.core_selling_points -----
        spr = payload.get("selling_point_recommendations") or {}
        if isinstance(spr, dict):
            _absorb(spr.get("core_selling_points"), default_core=True)

        # ----- v2 富结构：summary.top_decision_attributes[].top_values -----
        summary_block = payload.get("summary") or {}
        if isinstance(summary_block, dict):
            for attr_block in summary_block.get("top_decision_attributes") or []:
                if not isinstance(attr_block, dict):
                    continue
                for v in attr_block.get("top_values") or []:
                    _absorb([v])

        # ----- v1 简化结构与历史兼容 -----
        _absorb(payload.get("selling_point_strategy"))
        _absorb(payload.get("key_decision_attrs"))
        _absorb(payload.get("search_decision"), env="search")
        _absorb(payload.get("purchase_decision"), env="purchase")
        _absorb(payload.get("core_factors"), default_core=True)
        _absorb(payload.get("non_core_factors"), default_core=False)

    # 同时出现在 search 与 purchase 两个环节的卖点默认升为 core
    for name, envs in factor_envs.items():
        if {"search", "purchase"}.issubset(envs):
            entry = auth.get(name)
            if entry is not None:
                entry["is_core_factor"] = True
    return auth


def load_kano_thresholds(config_path: Optional[str]) -> Tuple[str, Dict[str, Dict[str, float]], Dict[str, float]]:
    """从 default_config.json 读取 kano_thresholds 和独特性阈值。"""
    profile = "default"
    presets = DEFAULT_KANO_PRESETS
    uniq = dict(DEFAULT_UNIQUENESS)
    if config_path and os.path.exists(config_path):
        try:
            cfg = load_json(config_path)
            kt = cfg.get("kano_thresholds") or {}
            profile = kt.get("profile") or "default"
            file_presets = kt.get("presets") or {}
            if file_presets:
                merged: Dict[str, Dict[str, Dict[str, float]]] = dict(DEFAULT_KANO_PRESETS)
                for k, v in file_presets.items():
                    merged[k] = v
                presets = merged
            spu = cfg.get("selling_point_uniqueness") or {}
            for k, v in spu.items():
                uniq[k] = v
        except Exception:
            pass
    if profile not in presets:
        profile = "default"
    return profile, presets, uniq


# --------- 维度聚合 ---------
def flatten_items(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    for band in raw.get("bands", []):
        band_label = band.get("band")
        for item in band.get("items", []):
            flat.append({**item, "band": band_label})
    return flat


def compute_band_share(
    flat_items: List[Dict[str, Any]],
    raw: Dict[str, Any],
    total_items: int,
    total_pay_min: int,
    top_n: int,
) -> List[Dict[str, Any]]:
    band_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in flat_items:
        band_groups[item["band"]].append(item)

    result: List[Dict[str, Any]] = []
    for band in raw.get("bands", []):
        band_label = band.get("band")
        items = band_groups.get(band_label, [])
        item_count = len(items)
        pay_min_sum = sum(int(it.get("pay_byr_cnt_min") or 0) for it in items)
        sorted_items = sorted(items, key=lambda x: int(x.get("pay_byr_cnt_min") or 0), reverse=True)
        head_pay = sum(int(it.get("pay_byr_cnt_min") or 0) for it in sorted_items[:top_n])
        top_concentration = (head_pay / pay_min_sum * 100) if pay_min_sum else 0.0
        result.append({
            "band": band_label,
            "min_price": band.get("min_price", ""),
            "max_price": band.get("max_price", ""),
            "item_count": item_count,
            "item_share": safe_round(item_count / total_items * 100 if total_items else 0),
            "pay_byr_cnt_min": pay_min_sum,
            "pay_byr_cnt_share": safe_round(pay_min_sum / total_pay_min * 100 if total_pay_min else 0),
            "top_concentration": safe_round(top_concentration),
        })
    return result


def compute_brand_share(
    flat_items: List[Dict[str, Any]],
    attrs_map: Dict[str, Dict[str, Any]],
    total_items: int,
    total_pay_min: int,
) -> List[Dict[str, Any]]:
    brand_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in flat_items:
        attr = attrs_map.get(str(item.get("item_id"))) or {}
        brand = attr.get("brand") or "未识别品牌"
        brand_groups[brand].append({**item, "_attr": attr})

    result: List[Dict[str, Any]] = []
    for brand, items in brand_groups.items():
        item_count = len(items)
        pay_min_sum = sum(int(it.get("pay_byr_cnt_min") or 0) for it in items)
        band_counter: Dict[str, int] = defaultdict(int)
        for it in items:
            band_counter[it.get("band")] += 1
        top_bands = [b for b, _ in sorted(band_counter.items(), key=lambda x: -x[1])[:2]]
        sorted_items = sorted(items, key=lambda x: int(x.get("pay_byr_cnt_min") or 0), reverse=True)
        head_item_ids = [it.get("item_id") for it in sorted_items[:3]]
        result.append({
            "brand": brand,
            "item_count": item_count,
            "item_share": safe_round(item_count / total_items * 100 if total_items else 0),
            "pay_byr_cnt_min": pay_min_sum,
            "pay_byr_cnt_share": safe_round(pay_min_sum / total_pay_min * 100 if total_pay_min else 0),
            "top_bands": top_bands,
            "head_item_ids": head_item_ids,
        })
    result.sort(key=lambda x: x["pay_byr_cnt_share"] or 0, reverse=True)
    return result


# --------- 卖点聚合（含电商版 KANO 量化与规则初判） ---------
def judge_kano_rule(
    d: Optional[float],
    p: Optional[float],
    r: Optional[float],
    h: Optional[float],
    presets: Dict[str, Dict[str, float]],
    is_core_factor: bool,
    item_count: Optional[int] = None,
) -> Tuple[str, str, Dict[str, bool]]:
    """电商版 KANO 规则初判：D/P/R/H 多条件 AND，is_core_factor 放宽 D/P 门槛 20%。

    返回：(kano_initial_suggestion, kano_rule_hit, rule_match_detail)

    v1.2 修复：R4 无差异型采用严格 AND，且小样本（item_count < min_item_count）不判 R4。
    """
    def _scale(v: Optional[float], factor: float) -> Optional[float]:
        return None if v is None else v * factor

    factor_d = 0.8 if is_core_factor else 1.0
    factor_p_max = 1.2 if is_core_factor else 1.0  # is_core 时 P 上限放宽

    rule_match = {
        "R1_basic": False,
        "R2_expected": False,
        "R3_excitement": False,
        "R4_indifferent": False,
    }

    # R1 基础型
    r1 = presets["R1"]
    if (d is not None and d >= r1.get("d_min", 0.50) * factor_d
            and p is not None and p > r1.get("p_min", 0.60) * factor_d
            and r is not None and r1.get("r_min", 0.85) <= r <= r1.get("r_max", 1.15)):
        rule_match["R1_basic"] = True

    # R2 期望型
    r2 = presets["R2"]
    if (d is not None and d >= r2.get("d_min", 0.30) * factor_d
            and p is not None and r2.get("p_min", 0.20) <= p <= r2.get("p_max", 0.70) * factor_p_max
            and r is not None and r > r2.get("r_min", 1.15)
            and (h is None or h >= r2.get("h_min", 1.0))):
        rule_match["R2_expected"] = True

    # R3 兴奋型（H ≥ 1.3 硬约束）
    r3 = presets["R3"]
    if (d is not None and d >= r3.get("d_min", 0.08) * factor_d
            and p is not None and p < r3.get("p_max", 0.20) * factor_p_max
            and r is not None and r >= r3.get("r_min", 1.50)
            and h is not None and h >= r3.get("h_min", 1.30)):
        rule_match["R3_excitement"] = True

    # R4 无差异型（v1.2 严格 AND）：D ≤ d_max AND R ≤ r_max AND item_count ≥ min_item_count
    # - 小样本（item_count < min_item_count）不判 R4，留 R0 给模型基于卖点语义决策
    # - 移除原 d_p_ratio_max 兜底（中等 P 时易误伤），改为纯 D&R 双门槛
    r4 = presets["R4"]
    min_cnt = r4.get("min_item_count", 5)
    cond_d_low = d is not None and d <= r4.get("d_max", 0.02)
    cond_r_low = r is not None and r <= r4.get("r_max", 0.80)
    cond_cnt_ok = item_count is None or item_count >= min_cnt
    if cond_d_low and cond_r_low and cond_cnt_ok:
        rule_match["R4_indifferent"] = True

    # 优先级：R3 > R2 > R1 > R4 > R0
    if rule_match["R3_excitement"]:
        return "兴奋型", "R3", rule_match
    if rule_match["R2_expected"]:
        return "期望型", "R2", rule_match
    if rule_match["R1_basic"]:
        return "基础型", "R1", rule_match
    if rule_match["R4_indifferent"]:
        return "无差异型", "R4", rule_match
    return "未命中", "R0", rule_match


def judge_uniqueness(p_coverage: Optional[float], uniq_cfg: Dict[str, float]) -> str:
    if p_coverage is None:
        return "未知"
    if p_coverage < uniq_cfg.get("unique_max_coverage", 0.10):
        return "独特"
    if p_coverage > uniq_cfg.get("homogenized_min_coverage", 0.50):
        return "同质化"
    return "差异化适中"


def compute_selling_point_share(
    flat_items: List[Dict[str, Any]],
    attrs_map: Dict[str, Dict[str, Any]],
    total_items: int,
    total_pay_min: int,
    top_n: int,
    band_labels: List[str],
    authority_map: Dict[str, Dict[str, Any]],
    presets: Dict[str, Dict[str, float]],
    uniq_cfg: Dict[str, float],
) -> List[Dict[str, Any]]:
    """按卖点聚合占比 + 计算电商版 KANO 量化指标 + 规则初判。"""
    # ---- 1) 全局参考量 ----
    # top10（全局支付买家数下界排序）用于 H_head_support
    flat_sorted = sorted(flat_items, key=lambda x: int(x.get("pay_byr_cnt_min") or 0), reverse=True)
    top10_ids = {str(it.get("item_id")) for it in flat_sorted[:10]}
    # 全局商品代理价（用于 E_price_premium）
    item_proxy_price: Dict[str, Optional[float]] = {}
    for it in flat_items:
        item_proxy_price[str(it.get("item_id"))] = parse_band_midprice(it.get("band"))
    valid_prices = [v for v in item_proxy_price.values() if v is not None]
    overall_avg_price = (sum(valid_prices) / len(valid_prices)) if valid_prices else None

    # ---- 2) 按卖点分组 ----
    sp_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    sp_kano_attr: Dict[str, str] = {}
    for item in flat_items:
        attr = attrs_map.get(str(item.get("item_id"))) or {}
        sps = attr.get("selling_points") or []
        kano = attr.get("kano_layer")
        for sp in sps:
            if not sp:
                continue
            sp_groups[sp].append(item)
            if sp not in sp_kano_attr and kano:
                sp_kano_attr[sp] = kano

    # ---- 3) 卖点级指标计算 ----
    result: List[Dict[str, Any]] = []
    for sp, items in sp_groups.items():
        item_count = len(items)
        pay_min_sum = sum(int(it.get("pay_byr_cnt_min") or 0) for it in items)
        sorted_items = sorted(items, key=lambda x: int(x.get("pay_byr_cnt_min") or 0), reverse=True)
        head_pay = sum(int(it.get("pay_byr_cnt_min") or 0) for it in sorted_items[:top_n])
        top_concentration = (head_pay / pay_min_sum * 100) if pay_min_sum else 0.0
        head_item_ids = [it.get("item_id") for it in sorted_items[:3]]

        # D / P / R
        d = (pay_min_sum / total_pay_min) if total_pay_min else None
        p = (item_count / total_items) if total_items else None
        r = None
        if d is not None and p is not None and p > 0:
            r = d / p

        # H：top10 内该卖点覆盖率 / 整体卖点覆盖率
        top10_with_sp = sum(1 for it in items if str(it.get("item_id")) in top10_ids)
        top10_coverage = top10_with_sp / 10.0 if top10_ids else None
        h = None
        if p and p > 0 and top10_coverage is not None:
            h = top10_coverage / p

        # E：含该卖点商品代理价均值 / 整体代理价均值
        sp_prices = [item_proxy_price.get(str(it.get("item_id"))) for it in items]
        sp_prices = [v for v in sp_prices if v is not None]
        sp_avg_price = (sum(sp_prices) / len(sp_prices)) if sp_prices else None
        e = None
        if sp_avg_price is not None and overall_avg_price and overall_avg_price > 0:
            e = sp_avg_price / overall_avg_price

        # band_distribution：该卖点在每个 band 的商品数占比
        band_counter: Dict[str, int] = defaultdict(int)
        for it in items:
            band_counter[it.get("band")] += 1
        band_distribution = {}
        for bl in band_labels:
            cnt = band_counter.get(bl, 0)
            band_distribution[bl] = safe_round_ratio(cnt / item_count) if item_count else 0.0

        # 类目权威
        ca = authority_map.get(sp) or {
            "is_key_decision_attr": False,
            "weight_rank": None,
            "is_core_factor": False,
        }

        # KANO 规则初判
        suggestion, rule_hit, rule_match = judge_kano_rule(
            d=d, p=p, r=r, h=h, presets=presets,
            is_core_factor=bool(ca.get("is_core_factor")),
            item_count=item_count,
        )

        # 独特性
        uniq_verdict = judge_uniqueness(p, uniq_cfg)

        result.append({
            "selling_point": sp,
            # 兼容字段（HTML/Excel 旧逻辑）
            "kano_layer": suggestion,             # 临时兜底为初判，模型终判后会回灌
            "item_count": item_count,
            "item_share": safe_round(item_count / total_items * 100 if total_items else 0),
            "pay_byr_cnt_min": pay_min_sum,
            "pay_byr_cnt_share": safe_round(pay_min_sum / total_pay_min * 100 if total_pay_min else 0),
            "top_concentration": safe_round(top_concentration),
            "head_item_ids": head_item_ids,
            # KANO 量化指标（小数比率，保留 3 位）
            "metrics": {
                "D_buyer_share": safe_round_ratio(d),
                "P_item_coverage": safe_round_ratio(p),
                "R_premium": safe_round_ratio(r, 2) if r is not None else None,
                "H_head_support": safe_round_ratio(h, 2) if h is not None else None,
                "E_price_premium": safe_round_ratio(e, 2) if e is not None else None,
                "band_distribution": band_distribution,
            },
            # 类目权威（来自 item-selling-point-alg-strategy）
            "category_authority": {
                "is_key_decision_attr": bool(ca.get("is_key_decision_attr")),
                "weight_rank": ca.get("weight_rank"),
                "is_core_factor": bool(ca.get("is_core_factor")),
            },
            # 脚本规则初判（最终 KANO 由模型 Step 5.1 二次判定）
            "kano_initial_suggestion": suggestion,
            "kano_rule_hit": rule_hit,
            "rule_match_detail": rule_match,
            "kano_decision_source": "rule_initial",  # 模型终判后会改写为 model_final
            # 独特性判定（脚本硬规则，模型不可改写）
            "uniqueness_verdict": uniq_verdict,
        })

    # 按支付买家数占比降序
    result.sort(key=lambda x: x.get("pay_byr_cnt_share") or 0, reverse=True)
    return result


# --------- 品牌集中度 ---------
def compute_concentration(brand_share: List[Dict[str, Any]]) -> Dict[str, Any]:
    """品牌集中度 CR1 / CR3 / CR5（按 pay_byr_cnt_share 排序，未识别品牌剔除）。"""
    cleaned = [b for b in brand_share if b.get("brand") and b.get("brand") != "未识别品牌"]
    sorted_brands = sorted(cleaned, key=lambda x: x.get("pay_byr_cnt_share") or 0, reverse=True)

    def _cr(n: int) -> Optional[float]:
        if not sorted_brands:
            return None
        share_sum = sum((b.get("pay_byr_cnt_share") or 0) for b in sorted_brands[:n])
        return safe_round(share_sum)

    return {
        "CR1": _cr(1),
        "CR3": _cr(3),
        "CR5": _cr(5),
        "head_brands": [b.get("brand") for b in sorted_brands[:5]],
    }


# --------- KANO 终判回灌（独立分支） ---------
VALID_KANO_LAYERS = {"基础型", "期望型", "兴奋型", "无差异型"}


def _normalize_kano_final_entry(entry: Any) -> Dict[str, Any]:
    """将 kano_final.json 中单条记录归一化为字典 schema。

    兼容三种历史写法：
    1. 字典含 kano_final/kano_layer 等字段（推荐）
    2. 字典将 kano_final 写成字符串（旧版示例）
    3. 直接是字符串（最不规范，但仍尝试兜底）
    """
    if isinstance(entry, str):
        return {"kano_layer": entry}
    if not isinstance(entry, dict):
        return {}
    out: Dict[str, Any] = {}
    raw_layer = entry.get("kano_layer") or entry.get("kano_final") or entry.get("final_layer")
    if isinstance(raw_layer, dict):
        # 旧版可能把 kano_final 又包一层 dict
        raw_layer = raw_layer.get("kano_layer") or raw_layer.get("kano_final")
    if isinstance(raw_layer, str) and raw_layer.strip():
        out["kano_layer"] = raw_layer.strip()
    for k in ("agree_with_rule", "override_reason", "confidence", "evidence_summary"):
        if k in entry and entry[k] is not None:
            out[k] = entry[k]
    return out


def merge_kano_final(market_share_path: str, kano_final_path: str, out_path: Optional[str] = None,
                     allow_overwrite: Sequence[str] = ()) -> Dict[str, Any]:
    """把模型终判结果回灌进 market_share.json 的 selling_point_share[*]。

    回灌规则：
    - selling_point_share[i].kano_final 始终写成 dict
      （含 kano_layer/agree_with_rule/override_reason/confidence/evidence_summary）
    - 同步覆写 kano_layer 字段，便于旧版下游脚本直接读
    - kano_decision_source 改写为 "model_final"
    - kano_layer 不在合法集合时直接拒绝（不静默吃掉异常）
    """
    share = load_json(market_share_path)
    final_doc = load_json(kano_final_path)
    final_list = final_doc.get("selling_points") if isinstance(final_doc, dict) else final_doc
    if not isinstance(final_list, list):
        raise ValueError("kano_final.json 顶层应为 dict.selling_points 数组或数组本身")

    # 建索引：selling_point -> normalized
    final_map: Dict[str, Dict[str, Any]] = {}
    for entry in final_list:
        if not isinstance(entry, dict):
            continue
        sp_name = entry.get("selling_point") or entry.get("name")
        if not sp_name:
            continue
        norm = _normalize_kano_final_entry(entry)
        layer = norm.get("kano_layer")
        if layer and layer not in VALID_KANO_LAYERS:
            raise ValueError(f"卖点[{sp_name}]的 kano_layer={layer!r} 不在合法集合 {VALID_KANO_LAYERS}")
        final_map[sp_name] = norm

    merged_count = 0
    miss = []
    for sp in share.get("selling_point_share", []) or []:
        sp_name = sp.get("selling_point")
        if not sp_name:
            continue
        norm = final_map.get(sp_name)
        if not norm:
            miss.append(sp_name)
            continue
        # kano_final 强制写成 dict（防止下游 .get 报错）
        existing = sp.get("kano_final") if isinstance(sp.get("kano_final"), dict) else {}
        existing.update(norm)
        sp["kano_final"] = existing
        if existing.get("kano_layer"):
            sp["kano_layer"] = existing["kano_layer"]
        sp["kano_decision_source"] = "model_final"
        # 若模型未填 agree_with_rule，则按 final == initial 推断
        if "agree_with_rule" not in existing:
            init = sp.get("kano_initial_suggestion")
            if existing.get("kano_layer") and init:
                existing["agree_with_rule"] = existing["kano_layer"] == init
        merged_count += 1

    share["kano_final_merged"] = True
    share["kano_final_merged_count"] = merged_count
    share["kano_final_missed"] = miss

    target = out_path or market_share_path
    # 回灌是对本技能自有产物的设计内增量（⑤）：目标即 --share 时自授权覆盖（仍会先备份原件）；
    # 写到别的路径则回到常规 artifact 覆盖守卫，需调用方精确授权。
    same_target = Path(target).expanduser().resolve() == Path(market_share_path).expanduser().resolve()
    authorized = [os.path.basename(target)] if same_target else list(allow_overwrite)
    write_record = guarded_write_json(target, share, allow_overwrite=authorized)

    print(f"[analyze_market_share] merge_kano_final merged={merged_count} missed={len(miss)} -> {target}"
          f" ({write_record['action']}"
          + (f", backup={write_record['backup']}" if write_record.get("backup") else "") + ")")
    if miss:
        print(f"[analyze_market_share] 以下卖点在 kano_final.json 中未找到：{miss}", file=sys.stderr)
    return share


# --------- 主流程 ---------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="品类市场占比 + KANO 量化分析")
    parser.add_argument("--raw", required=False, help="top_items_raw.json 路径（计算模式必填）")
    parser.add_argument("--attrs", required=False, help="item_attributes.json 路径（计算模式必填）")
    parser.add_argument("--out", required=False, help="market_share.json 输出路径（计算模式必填）")
    parser.add_argument("--strategy", default=None,
                        help="可选：category_selling_point_strategy.json 路径（类目权威外部信号）")
    parser.add_argument("--config", default=None,
                        help="可选：default_config.json 路径（KANO 阈值/独特性阈值）")
    parser.add_argument("--top-n", type=int, default=10, help="头部集中度 TopN，默认 10")
    parser.add_argument("--merge-kano-final", default=None,
                        help="回灌模式：传入 kano_final.json 路径，将模型终判合并进 --share 指向的 market_share.json")
    parser.add_argument("--share", default=None,
                        help="回灌模式必填：已存在的 market_share.json 路径")
    parser.add_argument("--allow-overwrite", action="append", default=[], metavar="REL_PATH",
                        help="逐路径精确授权覆盖已存在的 artifact 产物"
                             "（如 中间数据文件/market_share.json），可重复传入；覆盖前自动备份")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 回灌模式：与计算模式互斥
    if args.merge_kano_final:
        if not args.share:
            raise SystemExit("--merge-kano-final 模式必须同时提供 --share <market_share.json>")
        merge_kano_final(args.share, args.merge_kano_final, out_path=args.out or args.share,
                         allow_overwrite=args.allow_overwrite)
        return

    # 计算模式参数齐全性校验
    missing = [k for k in ("raw", "attrs", "out") if not getattr(args, k)]
    if missing:
        raise SystemExit(f"计算模式缺少必填参数：--{' --'.join(missing)}")

    # 默认配置路径：scripts/../config/default_config.json
    default_config_path = str(
        Path(__file__).resolve().parent.parent / "config" / "default_config.json"
    )
    config_path = args.config or (default_config_path if os.path.exists(default_config_path) else None)

    profile, presets, uniq_cfg = load_kano_thresholds(config_path)
    raw = load_json(args.raw)
    attrs_map = load_attrs_map(args.attrs)
    authority_map = load_strategy_authority(args.strategy)

    flat_items = flatten_items(raw)
    total_items = len(flat_items)
    total_pay_min = sum(int(it.get("pay_byr_cnt_min") or 0) for it in flat_items)
    band_labels = [b.get("band") for b in raw.get("bands", []) if b.get("band")]

    band_share = compute_band_share(flat_items, raw, total_items, total_pay_min, args.top_n)
    brand_share = compute_brand_share(flat_items, attrs_map, total_items, total_pay_min)
    selling_point_share = compute_selling_point_share(
        flat_items=flat_items,
        attrs_map=attrs_map,
        total_items=total_items,
        total_pay_min=total_pay_min,
        top_n=args.top_n,
        band_labels=band_labels,
        authority_map=authority_map,
        presets=presets.get(profile, presets["default"]),
        uniq_cfg=uniq_cfg,
    )
    concentration = compute_concentration(brand_share)

    payload: Dict[str, Any] = {
        "category": raw.get("category"),
        "category_id": raw.get("category_id"),
        "stat_period": raw.get("stat_period"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_items": total_items,
            "total_pay_byr_cnt_min": total_pay_min,
            "top_n": args.top_n,
        },
        # 元信息：本次脚本初判使用的阈值档位与独特性阈值，便于报告/审计
        "kano_profile": profile,
        "kano_thresholds_used": presets.get(profile, presets["default"]),
        "uniqueness_thresholds": uniq_cfg,
        "category_authority_loaded": bool(authority_map),
        "category_authority_count": len(authority_map),
        "band_share": band_share,
        "brand_share": brand_share,
        "selling_point_share": selling_point_share,
        "brand_concentration": concentration,
    }

    out_path = args.out
    write_record = guarded_write_json(out_path, payload, allow_overwrite=args.allow_overwrite)

    print(f"[analyze_market_share] profile={profile} authority={len(authority_map)} "
          f"items={total_items} selling_points={len(selling_point_share)} -> {out_path}"
          f" ({write_record['action']}"
          + (f", backup={write_record['backup']}" if write_record.get("backup") else "") + ")")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"[analyze_market_share] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
