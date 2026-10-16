# -*- coding: utf-8 -*-
"""category-market-analysis 消费方验签器（输入侧，只验签不深算）。

职责：
1. C2 榜单产物 top_items_raw.json：
   - 有 validation 凭证（v2）→ 只验 status==passed + payloadHash 一致；
   - 无凭证（v1，迁移期原技能产物）→ 做最小 Schema 断言并输出 warning。
2. C3 卖点策略 category_selling_point_strategy.json（生产方 category-top-items-fetch 的三态契约）：
   - schemaVersion==1、mode、requestId、source 白名单、consumer_decision_factors 富结构断言；
   - status==ready → 正常；
   - status==no_data（依赖可达但类目确无决策属性）→ 降级信号（stdout degraded=true，退出码 0）；
   - status==unavailable + degraded==true（取数侧没取到决策属性，由 strategy_handoff.py degrade 落盘）
     → 降级信号（stdout degraded=true、degradeReason=dependency_failed，退出码 0）；
   - 手写占位（source==placeholder 或带 unavailable_reason 但无降级协议标记）/ 结构不符
     → 失败退出码 2（禁止按猜测字段硬算、禁止伪造占位）。
3. 跨产物身份一致性：top_items.cate_id == strategy.category_id。

用法：
    python3 validate_input.py --top-items <top_items_raw.json> --strategy <category_selling_point_strategy.json>
退出码：0=可进入分析（含降级）；2=输入不合格，禁止分析。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

STRATEGY_SOURCES = ("category-decision-factor-fetch", "item-selling-point-alg-strategy")


def _load(path: str) -> Tuple[Any, List[str]]:
    p = Path(path)
    if not p.exists():
        return None, [f"文件不存在: {p}"]
    try:
        return json.loads(p.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"JSON 解析失败: {p} → {exc}"]


def _payload_hash(payload: Dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "validation"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_top_items(payload: Any) -> Tuple[List[str], List[str]]:
    """返回 (errors, warnings)。"""
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(payload, dict):
        return ["top_items_raw 顶层必须是 object"], warnings

    cred = payload.get("validation")
    if isinstance(cred, dict):
        # v2：只验签，不重复深校验（校验责任在生产方）
        if cred.get("status") != "passed":
            errors.append(f"top_items validation.status != passed: {cred.get('status')!r}")
        if cred.get("payloadHash") != _payload_hash(payload):
            errors.append("top_items validation.payloadHash 与正文不一致（可能被篡改/部分覆写）")
        return errors, warnings

    # v1（迁移期）：最小 Schema 断言
    warnings.append("top_items_raw 无 validation 凭证（v1 产物），已做最小 Schema 断言")
    for f in ("cate_id", "rank_type", "date_type", "bands"):
        if f not in payload:
            errors.append(f"top_items 顶层缺字段: {f}")
    bands = payload.get("bands")
    if not isinstance(bands, list) or not bands:
        errors.append("top_items.bands 必须为非空数组")
        return errors, warnings
    for bi, band in enumerate(bands):
        if not isinstance(band, dict) or not isinstance(band.get("items"), list):
            errors.append(f"top_items.bands[{bi}] 结构不符（items 必须为数组）")
            continue
        for ii, it in enumerate(band["items"][:5]):  # 抽检前 5 条
            if not isinstance(it, dict) or not str(it.get("item_id") or "").strip():
                errors.append(f"top_items.bands[{bi}].items[{ii}] 缺少非空 item_id")
            elif "title" not in it or "pay_byr_cnt_min" not in it:
                errors.append(f"top_items.bands[{bi}].items[{ii}] 缺少 title/pay_byr_cnt_min")
    return errors, warnings


def is_degraded_strategy(payload: Any) -> bool:
    """协议降级判定：no_data（权威空结果）/ unavailable（取数侧没取到决策属性）。"""
    if not isinstance(payload, dict):
        return False
    return (
        str(payload.get("status") or "") in ("no_data", "unavailable")
        or payload.get("degraded") is True
    )


def check_strategy(payload: Any) -> Tuple[List[str], str]:
    """返回 (errors, status)。status ∈ ready / no_data / unavailable / invalid。"""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["strategy 顶层必须是 object"], "invalid"
    degraded = is_degraded_strategy(payload)
    # 手写占位仍然拒收：降级必须带协议标记（status=no_data 由依赖返回，
    # status=unavailable + degraded=true 由取数技能的 strategy_handoff.py degrade 写出）。
    if payload.get("source") == "placeholder" or (
        payload.get("unavailable_reason") and not degraded
    ):
        errors.append(
            "strategy 是手写占位文件；取数失败必须由 category-top-items-fetch 的 "
            "strategy_handoff.py degrade 写降级契约"
            "（status=unavailable + degraded=true + degradeReason）"
        )
        return errors, "invalid"
    if payload.get("schemaVersion") != 1:
        errors.append(f"strategy.schemaVersion 必须为 1，收到 {payload.get('schemaVersion')!r}")
    if payload.get("mode") != "category_decision_factors":
        errors.append("strategy.mode 必须为 category_decision_factors")
    if payload.get("source") not in STRATEGY_SOURCES:
        errors.append(f"strategy.source 必须 ∈ {STRATEGY_SOURCES}")
    if not payload.get("requestId"):
        errors.append("strategy 缺少 requestId")
    if not (payload.get("category_id") or payload.get("cateId")):
        errors.append("strategy 缺少 category_id")

    status = str(payload.get("status") or "") or None
    if status == "no_data":
        return errors, "no_data"
    if status == "unavailable":
        # 依赖失败降级：要求降级标记齐全 + 有真实失败原因，避免拿空文件冒充降级
        if payload.get("degraded") is not True:
            errors.append("strategy.status=unavailable 必须带 degraded=true（降级协议标记）")
        if payload.get("degradeReason") != "dependency_failed":
            errors.append("strategy.status=unavailable 时 degradeReason 必须为 dependency_failed")
        if not str(payload.get("unavailable_reason") or "").strip():
            errors.append("strategy.status=unavailable 必须写 unavailable_reason（真实失败原因）")
        return errors, "unavailable"
    if status not in (None, "ready"):
        errors.append(
            f"strategy.status 必须 ∈ {{ready, no_data, unavailable}}，收到 {status!r}"
        )
        return errors, "invalid"

    cdf = payload.get("consumer_decision_factors")
    if not isinstance(cdf, dict):
        errors.append("strategy 缺少 consumer_decision_factors 对象")
        return errors, "invalid"
    has_attr = False
    for scene_name in ("search", "purchase"):
        scene = cdf.get(scene_name)
        if not isinstance(scene, dict):
            continue
        result = (scene.get("data") or {}).get("result") if isinstance(scene.get("data"), dict) else None
        if not isinstance(result, list):
            continue
        for row in result:
            if isinstance(row, dict) and row.get("pname") and "std_score_p" in row and row.get("v_list"):
                has_attr = True
                break
    if not has_attr and not payload.get("selling_point_strategy"):
        errors.append("strategy 无有效权威信号（cdf 富结构与 selling_point_strategy 均为空且 status!=no_data）")
        return errors, "invalid"
    return errors, "ready"


def main() -> int:
    parser = argparse.ArgumentParser(description="category-market-analysis 输入验签")
    parser.add_argument("--top-items", required=True, help="top_items_raw.json 路径")
    parser.add_argument("--strategy", required=True, help="category_selling_point_strategy.json 路径")
    args = parser.parse_args()

    errors: List[str] = []
    warnings: List[str] = []

    top, errs = _load(args.top_items)
    errors.extend(errs)
    strategy, errs = _load(args.strategy)
    errors.extend(errs)

    strategy_status = "invalid"
    if top is not None:
        e, w = check_top_items(top)
        errors.extend(e)
        warnings.extend(w)
    if strategy is not None:
        e, strategy_status = check_strategy(strategy)
        errors.extend(e)

    # 跨产物身份一致性（编排断链防护：cateId 必须同一类目）
    if isinstance(top, dict) and isinstance(strategy, dict):
        top_cate = str(top.get("cate_id") or "")
        strat_cate = str(strategy.get("category_id") or strategy.get("cateId") or "")
        if top_cate and strat_cate and top_cate != strat_cate:
            errors.append(f"身份不一致：top_items.cate_id={top_cate} != strategy.category_id={strat_cate}")

    if errors:
        print(f"[FAIL] 输入验签失败（{len(errors)} 项），禁止进入分析：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    degraded = strategy_status in ("no_data", "unavailable")
    degrade_reason = ""
    unavailable_reason = ""
    if degraded and isinstance(strategy, dict):
        degrade_reason = str(strategy.get("degradeReason") or strategy_status)
        unavailable_reason = str(strategy.get("unavailable_reason") or "")
    print(json.dumps({
        "success": True,
        "degraded": degraded,
        "strategyStatus": strategy_status,
        "degradeReason": degrade_reason,
        "unavailableReason": unavailable_reason,
        "topItemsStats": (top.get("stats") if isinstance(top, dict) else None),
        "warnings": warnings,
        "note": "degraded=true 时卖点提取走 references/category-decision-attributes.md 关键词表兜底，"
                "KANO 仅用脚本初判（无类目权威放宽），item_attributes.json 必须写 _warnings 记录降级原因，"
                "报告不得把降级说成已取得消费者决策属性" if degraded else "",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
