# -*- coding: utf-8 -*-
"""降级态 item_attributes.json 关键词兜底填充器。

仅在 strategy 处于降级态（status=no_data / unavailable / degraded=true）时可用：
此时权威词表为空，卖点匹配的唯一依据就是 references/category-decision-attributes.md
的「主词 / 同义词归一」表，属确定性字符串归一，无需模型逐条推理（600 条商品时尤甚）。

职责：把 build_skeleton.py --stage attributes 产出的骨架里的模型字段填完：
- brand            ← shop_title 品牌提取（店铺名后缀剥离；标题里的适配品牌一律不取，取不到写 null）
- selling_points   ← 标题命中关键词表主词（同义词归一为主词，按标题出现位置排序，上限 --max-points）
- selling_point_categories ← 命中主词按 8 大类分组
- selling_point_origins    ← 全部 reference_md（降级态无 authority 信号）
- kano_layer       ← 最显著卖点所属类别的 KANO 默认层（无卖点 → 无差异型）
- price_signal     ← 价格信号类命中（不进 selling_points）

纪律：
- 非降级态（status=ready）拒绝执行：有权威词表时必须走模型语义步（authority 优先于 reference_md）；
- 只替换 <待填> 占位符与空容器，已填内容默认不动（--force 才整条重填）；
- 锁定字段 itemId/band/authority_source/authority_count/_warnings 只读不改（_warnings 追加一条脚本留痕）；
- 词表事实源唯一：运行时解析 references/category-decision-attributes.md，解析不出可用词表即失败，
  绝不静默退化成空词表（否则会产出全空卖点的假结论）；
- 原地填充属不可逆写：item_attributes.json 属 `artifact`（见 write_guard.py），写回前先把原件
  备份到 `临时文件/write-backup-*/`（备份路径进 stdout），再走 .partial 原子替换。

用法：
    python3 fill_attributes_fallback.py \
        --raw <top_items_raw.json> --strategy <category_selling_point_strategy.json> \
        --attrs <item_attributes.json> [--keywords <category-decision-attributes.md>] \
        [--max-points 6] [--force]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import write_guard  # noqa: E402  写入分类 / 路径守卫 / 覆盖守卫

PLACEHOLDER = "<待填>"
ORIGIN = "reference_md"
PRICE_CATEGORY = "价格信号"
VALID_KANO_LAYERS = ("基础型", "期望型", "兴奋型", "无差异型")
DEFAULT_KEYWORDS_MD = Path(__file__).resolve().parent.parent / "references" / "category-decision-attributes.md"

# 店铺名后缀剥离表（长后缀在前，逐个尝试）。品牌识别规则见
# references/category-decision-attributes.md §四；脚本只做「店铺名 → 品牌」这一确定性分支。
SHOP_SUFFIXES = (
    "海外旗舰店", "官方旗舰店", "官方专卖店", "官方专营店", "全球购商品",
    "旗舰店", "专卖店", "专营店", "官方店", "自营店", "直营店", "企业店",
    "工厂店", "总代理", "经销店", "生活馆", "专柜", "官方",
)
# 店铺名中的平台/渠道噪声词，剥离后再取品牌
SHOP_NOISE = ("天猫超市", "天猫国际", "天猫", "淘宝", "京东", "拼多多", "海外", "全球购", "国际")


def _fail(messages: List[str], hint: str = "") -> None:
    for m in messages:
        print(f"[FAIL] {m}", file=sys.stderr)
    if hint:
        for line in hint.strip().splitlines():
            print(f"       {line}", file=sys.stderr)
    sys.exit(2)


def _load(path: str, label: str) -> Any:
    p = Path(path)
    if not p.exists():
        _fail([f"{label} 不存在: {p}"])
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail([f"{label} JSON 解析失败: {exc}"])


def _guarded_write(path: str, payload: dict) -> dict:
    """原地填充自有骨架属设计内覆盖：逐路径自授权，但必经守卫先备份原件再原子替换。"""
    try:
        return write_guard.write_json(path, payload, artifact_type="artifact",
                                      label=Path(path).name,
                                      allow_overwrite=[Path(path).name])
    except write_guard.WriteGuardError as exc:
        _fail([f"写入被守卫拒绝: {exc}"])


def _norm(text: str) -> str:
    """匹配用归一：去空白 + 小写，保证「A 醇」「SPF」这类写法可命中。"""
    return re.sub(r"\s+", "", str(text or "")).lower()


# ---------------------------------------------------------------------------
# 关键词表解析（事实源：references/category-decision-attributes.md）
# ---------------------------------------------------------------------------
def _split_row(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_keyword_table(md_text: str) -> Tuple[Dict[str, List[Tuple[str, List[str]]]], Dict[str, str]]:
    """解析 8 大类关键词词典与各类 KANO 默认层。

    返回 (categories, kano_default)：
    - categories: {类别: [(主词, [匹配变体...]), ...]}，保持 md 中的顺序
    - kano_default: {类别: KANO 默认层}
    """
    lines = md_text.splitlines()

    # ---- §二 8 大属性类别 → KANO 默认层 ----
    kano_default: Dict[str, str] = {}
    in_class_table = False
    for line in lines:
        if line.startswith("## ") and "属性类别" in line:
            in_class_table = True
            continue
        if in_class_table:
            if line.startswith("## ") or line.startswith("### "):
                break
            if not line.strip().startswith("|"):
                continue
            cells = _split_row(line)
            if len(cells) < 3 or cells[0] in ("类别",) or set(cells[0]) <= {"-", ":"}:
                continue
            layer = next((lay for lay in VALID_KANO_LAYERS if lay in cells[2]), "")
            if layer:
                kano_default[cells[0].strip()] = layer

    # ---- §三 各类关键词词典（### 3.x 类别名） ----
    categories: Dict[str, List[Tuple[str, List[str]]]] = {}
    current: Optional[str] = None
    for line in lines:
        heading = re.match(r"^###\s+3\.\d+\s+(.+?)\s*$", line)
        if heading:
            # 「成分/材质（名词）」→「成分」；「资质/口碑」→「资质」
            name = re.split(r"[（(]", heading.group(1))[0]
            current = name.split("/")[0].strip()
            categories.setdefault(current, [])
            continue
        if line.startswith("## "):
            current = None
            continue
        if not current or not line.strip().startswith("|"):
            continue
        cells = _split_row(line)
        if len(cells) < 2 or cells[0] in ("主词",) or set(cells[0]) <= {"-", ":"}:
            continue
        canonical = cells[0]
        if not canonical:
            continue
        # 同义词只按「、」「,」「，」切分：不切 "/"，避免 "316/304 不锈钢" 被拆出 "316" 这类危险短词
        synonyms = [s.strip() for s in re.split(r"[、,，]", cells[1]) if s.strip()]
        variants = [canonical] + synonyms
        # 主词自带 "/" 时（如「早晨/晚间」）拆出可匹配变体，规范名仍用表内主词
        if "/" in canonical:
            variants += [p.strip() for p in canonical.split("/") if len(p.strip()) >= 2]
        categories[current].append((canonical, variants))

    errors: List[str] = []
    if PRICE_CATEGORY not in categories:
        errors.append(f"关键词表缺少「{PRICE_CATEGORY}」小节（§3.8）")
    word_categories = [c for c, w in categories.items() if w and c != PRICE_CATEGORY]
    if len(word_categories) < 7:
        errors.append(f"关键词表仅解析出 {len(word_categories)} 个卖点类别（应为 7 个：功效/成分/场景/人群/工艺/资质/赠品）")
    total_words = sum(len(w) for w in categories.values())
    if total_words < 50:
        errors.append(f"关键词表仅解析出 {total_words} 个主词，明显少于预期（疑似 md 表格格式变更）")
    missing_layer = [c for c in word_categories if c not in kano_default]
    if missing_layer:
        errors.append(f"以下类别在 §二 表中查不到 KANO 默认层: {missing_layer}")
    if errors:
        _fail(
            errors,
            "关键词表是降级态卖点提取的唯一事实源，解析失败时禁止继续（否则会产出全空卖点的假结论）。\n"
            "请检查 references/category-decision-attributes.md 的 §二 类别表与 §3.x 词典表格式。",
        )
    return categories, kano_default


# ---------------------------------------------------------------------------
# 单条商品提取
# ---------------------------------------------------------------------------
def extract_brand(shop_title: str) -> Optional[str]:
    """从店铺名提取品牌；识别不出返回 None（禁止从标题取，避免适配品牌误判）。"""
    name = re.sub(r"[\s()（）\[\]【】]", "", str(shop_title or ""))
    if not name:
        return None
    for noise in SHOP_NOISE:
        name = name.replace(noise, "")
    for suffix in SHOP_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    else:
        if name.endswith("店"):
            name = name[:-1]
    name = name.strip("的-_·、")
    return name if len(name) >= 2 else None


def match_keywords(
    title: str,
    categories: Dict[str, List[Tuple[str, List[str]]]],
    canonical_set: set,
) -> List[Tuple[int, str, str]]:
    """返回命中列表 [(标题内位置, 类别, 主词)]，同义词已归一为主词。"""
    norm_title = _norm(title)
    if not norm_title:
        return []
    hits: List[Tuple[int, str, str]] = []
    for cat, words in categories.items():
        for canonical, variants in words:
            best = -1
            for variant in variants:
                nv = _norm(variant)
                if not nv:
                    continue
                # 同义词恰好是别的类目主词时跳过（如「三防」的同义词「防水」本身是功效主词，
                # 命中「防水」只应产出「防水」，不应连带产出「三防」）
                if nv != _norm(canonical) and variant in canonical_set:
                    continue
                pos = norm_title.find(nv)
                if pos >= 0 and (best < 0 or pos < best):
                    best = pos
            if best >= 0:
                hits.append((best, cat, canonical))
    return hits


def fill_item(
    item: Dict[str, Any],
    raw_item: Dict[str, Any],
    categories: Dict[str, List[Tuple[str, List[str]]]],
    canonical_set: set,
    kano_default: Dict[str, str],
    max_points: int,
    force: bool,
) -> None:
    hits = match_keywords(raw_item.get("title") or "", categories, canonical_set)
    price_hits = sorted([h for h in hits if h[1] == PRICE_CATEGORY])
    sp_hits = sorted([h for h in hits if h[1] != PRICE_CATEGORY])

    selling_points: List[str] = []
    grouped: Dict[str, List[str]] = {}
    for _pos, cat, canonical in sp_hits:
        if canonical in selling_points:
            continue
        if len(selling_points) >= max_points:
            break
        selling_points.append(canonical)
        grouped.setdefault(cat, []).append(canonical)

    if force or item.get("brand") == PLACEHOLDER:
        item["brand"] = extract_brand(raw_item.get("shop_title") or "")
    if force or not item.get("selling_points"):
        item["selling_points"] = selling_points
        item["selling_point_categories"] = grouped
        item["selling_point_origins"] = {sp: ORIGIN for sp in selling_points}
    if force or item.get("kano_layer") == PLACEHOLDER:
        first_cat = sp_hits[0][1] if sp_hits else None
        item["kano_layer"] = kano_default.get(first_cat, "期望型") if first_cat else "无差异型"
    if force or item.get("price_signal") in (None, PLACEHOLDER):
        item["price_signal"] = price_hits[0][2] if price_hits else None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def index_raw_items(raw: Any) -> Dict[str, Dict[str, Any]]:
    """展平 top_items_raw.bands[].items[]，并强校验上游输入结构。"""
    if not isinstance(raw, dict):
        _fail(["top_items_raw.json 顶层不是 object"])
    bands = raw.get("bands")
    if not isinstance(bands, list) or not bands:
        _fail(["top_items_raw.bands 缺失或不是非空数组，先确认取数技能产物完整"])

    index: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    for bi, band in enumerate(bands):
        if not isinstance(band, dict) or not isinstance(band.get("items"), list):
            errors.append(f"bands[{bi}] 结构不符（items 必须为数组）")
            continue
        for ii, it in enumerate(band["items"]):
            if not isinstance(it, dict):
                errors.append(f"bands[{bi}].items[{ii}] 不是 object")
                continue
            item_id = str(it.get("item_id") or "").strip()
            if not item_id:
                errors.append(f"bands[{bi}].items[{ii}] 缺少非空 item_id")
                continue
            if "title" not in it:
                errors.append(f"bands[{bi}].items[{ii}](item_id={item_id}) 缺少 title 字段，无法做关键词匹配")
                continue
            index.setdefault(item_id, it)
    if errors:
        _fail(errors[:12] + ([f"……另有 {len(errors) - 12} 条结构错误（已截断）"] if len(errors) > 12 else []),
              "输入结构不符合预期，禁止按猜测字段硬填；请让 category-top-items-fetch 重出 top_items_raw.json。")
    return index


def assert_degraded(strategy: Any) -> str:
    if not isinstance(strategy, dict):
        _fail(["category_selling_point_strategy.json 顶层不是 object"])
    status = str(strategy.get("status") or "")
    degraded = status in ("no_data", "unavailable") or strategy.get("degraded") is True
    if not degraded:
        _fail(
            [f"strategy 未处于降级态（status={status or '未声明'}），本脚本拒绝执行"],
            "非降级态存在类目权威词表，卖点提取必须走模型语义步（authority 优先于 reference_md），\n"
            "见 references/selling-point-extraction.md 两级匹配优先级。",
        )
    return str(strategy.get("degradeReason") or status or "degraded")


def main() -> int:
    parser = argparse.ArgumentParser(description="降级态 item_attributes 关键词兜底填充")
    parser.add_argument("--raw", required=True, help="top_items_raw.json")
    parser.add_argument("--strategy", required=True, help="category_selling_point_strategy.json（必须为降级态）")
    parser.add_argument("--attrs", required=True, help="item_attributes.json 骨架（build_skeleton.py --stage attributes 产出），原地填充")
    parser.add_argument("--keywords", default=str(DEFAULT_KEYWORDS_MD), help="关键词表 md（默认 references/category-decision-attributes.md）")
    parser.add_argument("--max-points", type=int, default=6, help="单商品保留卖点上限（默认 6）")
    parser.add_argument("--force", action="store_true", help="整条重填（含已填内容），默认只填 <待填> 与空容器")
    args = parser.parse_args()

    degrade_reason = assert_degraded(_load(args.strategy, "category_selling_point_strategy.json"))
    raw_index = index_raw_items(_load(args.raw, "top_items_raw.json"))

    attrs = _load(args.attrs, "item_attributes.json")
    if not isinstance(attrs, dict) or not isinstance(attrs.get("items"), list) or not attrs["items"]:
        _fail(["item_attributes.json 缺少非空 items[]"],
              "请先跑 build_skeleton.py --stage attributes 预填骨架，再跑本脚本。")

    kw_path = Path(args.keywords)
    if not kw_path.exists():
        _fail([f"关键词表不存在: {kw_path}"])
    categories, kano_default = parse_keyword_table(kw_path.read_text(encoding="utf-8"))
    canonical_set = {c for words in categories.values() for c, _ in words}

    # 骨架与原始数据身份一致性：条目不匹配说明骨架过期，禁止错位填充
    skeleton_ids = [str(it.get("itemId") or "") for it in attrs["items"] if isinstance(it, dict)]
    unknown = [i for i in skeleton_ids if i not in raw_index]
    if unknown:
        _fail([f"骨架中 {len(unknown)} 条 itemId 在 top_items_raw 中不存在（示例：{unknown[:5]}）"],
              "骨架与原始数据不一致，请用同一份 top_items_raw.json 重跑 build_skeleton.py --stage attributes --force。")

    for item in attrs["items"]:
        if not isinstance(item, dict):
            _fail(["items[] 中存在非 object 条目，骨架已损坏，请重跑 build_skeleton.py"])
        fill_item(item, raw_index[str(item["itemId"])], categories, canonical_set,
                  kano_default, args.max_points, args.force)

    total = len(attrs["items"])
    brand_filled = sum(1 for it in attrs["items"] if it.get("brand"))
    no_point = [str(it.get("itemId")) for it in attrs["items"] if not it.get("selling_points")]
    point_total = sum(len(it.get("selling_points") or []) for it in attrs["items"])
    price_filled = sum(1 for it in attrs["items"] if it.get("price_signal"))

    note = (
        f"关键词表兜底填充由 fill_attributes_fallback.py 完成（degradeReason={degrade_reason}）："
        f"{total} 条商品，品牌命中 {brand_filled} 条，卖点全部 origin=reference_md，"
        f"无卖点命中 {len(no_point)} 条"
    )
    warnings = attrs.get("_warnings")
    attrs["_warnings"] = ([w for w in warnings if str(w).strip()] if isinstance(warnings, list) else [])
    attrs["_warnings"].append(note)
    write_record = _guarded_write(args.attrs, attrs)

    summary = {
        "success": True,
        "output": args.attrs,
        "write": write_record,
        "degradeReason": degrade_reason,
        "items": total,
        "brandFilled": brand_filled,
        "brandNull": total - brand_filled,
        "sellingPointsAvg": round(point_total / total, 2) if total else 0,
        "itemsWithoutSellingPoint": len(no_point),
        "priceSignalFilled": price_filled,
        "keywordTable": str(kw_path),
        "origins": ORIGIN,
    }
    if total and len(no_point) / total > 0.30:
        summary["warning"] = (
            f"⚠️ {len(no_point)}/{total} 条商品未命中任何关键词（>30%），"
            f"该类目可能不在通用词典覆盖范围内：请按 category-decision-attributes.md 的类别定义人工补充这些商品，"
            f"示例 itemId={no_point[:5]}"
        )
    print(json.dumps(summary, ensure_ascii=False))
    print(f"下一步：python3 \"{Path(__file__).resolve().parent / 'verify_step.py'}\" --step Step3c --work-dir <work_dir>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
