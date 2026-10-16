# -*- coding: utf-8 -*-
"""category-market-analysis 模型产物骨架预填器（速度调优手段 2：骨架填空）。

消除模型从零生成大 JSON 的两处退化点：
- --stage attributes：读 top_items_raw.json + strategy 预填 item_attributes.json 骨架
  （itemId/band 为锁定字段脚本预填；brand/selling_points 等模型字段留 <待填> 占位符）。
- --stage kano：读 market_share.json 预填 kano_final.json 骨架
  （selling_point/kano_initial 为锁定字段；kano_final.* 模型字段留 <待填> 占位符）。

纪律：
- 模型只允许替换 <待填> 占位符与空容器，禁止增删条目、禁止改锁定字段；
- verify_step Step3c/Step4b 会拦截任何残留 <待填>（占位符必须填完）；
- 输出已存在时拒绝覆盖（防止覆盖已填内容），显式 --force 才允许重建；
- --force 重建属不可逆写：骨架属 `artifact`（见 write_guard.py），覆盖前先把原件备份到
  `临时文件/write-backup-*/`，备份路径写入 stdout；备份失败则不写；
- 写入统一走 write_guard：路径守卫 → 覆盖授权 → 备份 → .partial 原子替换。

用法：
    python3 build_skeleton.py --stage attributes --raw <top_items_raw.json> \
        --strategy <category_selling_point_strategy.json> --output <item_attributes.json>
    python3 build_skeleton.py --stage kano --share <market_share.json> --output <kano_final.json>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import write_guard  # noqa: E402  写入分类 / 路径守卫 / 覆盖守卫

PLACEHOLDER = "<待填>"


def _load(path: str, label: str):
    p = Path(path)
    if not p.exists():
        print(f"[FAIL] {label} 不存在: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[FAIL] {label} JSON 解析失败: {exc}", file=sys.stderr)
        sys.exit(2)


def _guarded_write(path: str, payload: dict, allow_overwrite=()) -> dict:
    """骨架属 artifact：覆盖（--force）前必先备份原件，守卫失败直接报错退出 2。"""
    try:
        return write_guard.write_json(path, payload, artifact_type="artifact",
                                      label=Path(path).name,
                                      allow_overwrite=allow_overwrite)
    except write_guard.WriteGuardError as exc:
        print(f"[FAIL] 写入被守卫拒绝: {exc}", file=sys.stderr)
        sys.exit(2)


def _count_authority(strategy: dict) -> int:
    """统计权威属性条数：cdf 富结构 pname 去重数，兼容 selling_point_strategy 简化形态。"""
    names = set()
    cdf = strategy.get("consumer_decision_factors") or {}
    for scene in ("search", "purchase"):
        result = ((cdf.get(scene) or {}).get("data") or {})
        rows = result.get("result") if isinstance(result, dict) else None
        for row in rows or []:
            if isinstance(row, dict) and row.get("pname"):
                names.add(str(row["pname"]))
    for rec in strategy.get("selling_point_strategy") or []:
        if isinstance(rec, dict) and rec.get("selling_point"):
            names.add(str(rec["selling_point"]))
    return len(names)


def build_attributes(raw: dict, strategy: dict) -> dict:
    items = []
    seen = set()
    for band in raw.get("bands") or []:
        band_name = band.get("band")
        for it in band.get("items") or []:
            item_id = str(it.get("item_id") or "").strip()
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            items.append({
                # ---- 锁定字段（脚本预填，模型禁改） ----
                "itemId": item_id,
                "band": band_name,
                # ---- 模型字段（占位符必须全部填完） ----
                "brand": PLACEHOLDER,
                "selling_points": [],
                "selling_point_categories": {},
                "selling_point_origins": {},
                "kano_layer": PLACEHOLDER,
            })
    if not items:
        print("[FAIL] top_items_raw.bands 无可用商品，无法预填骨架", file=sys.stderr)
        sys.exit(2)

    # 降级态：status=no_data（类目确无决策属性）/ status=unavailable（取数侧没取到决策属性）
    status = str(strategy.get("status") or "")
    degraded = status in ("no_data", "unavailable") or strategy.get("degraded") is True
    payload = {
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "attribute_taxonomy_version": "v1",
        "authority_source": strategy.get("source") or PLACEHOLDER,
        "authority_count": 0 if degraded else _count_authority(strategy),
        "items": items,
    }
    if degraded:
        reason = str(strategy.get("degradeReason") or status or "degraded")
        detail = str(strategy.get("unavailable_reason") or "").strip()
        warning = (
            f"category-decision-factor-fetch 降级（status={status or 'degraded'}"
            f"，degradeReason={reason}"
            + (f"，原因={detail}" if detail else "")
            + "），本次卖点匹配走 references/category-decision-attributes.md 关键词表兜底"
        )
        payload["_warnings"] = [warning]
    return payload


def build_kano(share: dict) -> dict:
    sp_share = share.get("selling_point_share")
    if not isinstance(sp_share, list) or not sp_share:
        print("[FAIL] market_share.selling_point_share 缺失或为空，先完成占比计算（③）", file=sys.stderr)
        sys.exit(2)
    selling_points = []
    for sp in sp_share:
        if not isinstance(sp, dict) or not sp.get("selling_point"):
            continue
        selling_points.append({
            # ---- 锁定字段（脚本预填，模型禁改） ----
            "selling_point": sp["selling_point"],
            "kano_initial": sp.get("kano_initial_suggestion") or PLACEHOLDER,
            # ---- 模型字段（占位符必须全部填完；agree_with_rule 填 true/false 布尔） ----
            "kano_final": {
                "kano_layer": PLACEHOLDER,
                "agree_with_rule": PLACEHOLDER,
                "override_reason": PLACEHOLDER,
                "confidence": PLACEHOLDER,
                "evidence_summary": PLACEHOLDER,
            },
        })
    return {"version": "v1", "selling_points": selling_points}


def main() -> int:
    parser = argparse.ArgumentParser(description="模型产物骨架预填")
    parser.add_argument("--stage", required=True, choices=["attributes", "kano"])
    parser.add_argument("--raw", help="top_items_raw.json（attributes 阶段必填）")
    parser.add_argument("--strategy", help="category_selling_point_strategy.json（attributes 阶段必填）")
    parser.add_argument("--share", help="market_share.json（kano 阶段必填）")
    parser.add_argument("--output", required=True, help="骨架输出路径")
    parser.add_argument("--force", action="store_true",
                        help="输出已存在时允许覆盖重建（不可逆：覆盖前自动备份原件到 临时文件/write-backup-*/）")
    args = parser.parse_args()

    exists = Path(args.output).exists()
    if exists and not args.force:
        print(f"[FAIL] 输出已存在，拒绝覆盖（防止丢失已填内容）：{args.output}\n"
              f"       确需重建请加 --force（覆盖前会把原件备份到 临时文件/write-backup-*/）", file=sys.stderr)
        return 2

    if args.stage == "attributes":
        if not args.raw or not args.strategy:
            print("[FAIL] attributes 阶段必须提供 --raw 与 --strategy", file=sys.stderr)
            return 2
        payload = build_attributes(_load(args.raw, "top_items_raw.json"),
                                   _load(args.strategy, "category_selling_point_strategy.json"))
        summary = {"stage": "attributes", "items": len(payload["items"]),
                   "authority_count": payload["authority_count"],
                   "degraded": "_warnings" in payload}
    else:
        if not args.share:
            print("[FAIL] kano 阶段必须提供 --share", file=sys.stderr)
            return 2
        payload = build_kano(_load(args.share, "market_share.json"))
        summary = {"stage": "kano", "sellingPoints": len(payload["selling_points"])}

    # --force 属对本脚本自有产物的显式重建授权：逐路径传给写入守卫，由守卫负责覆盖前备份
    write_record = _guarded_write(
        args.output, payload,
        allow_overwrite=[Path(args.output).name] if (exists and args.force) else ())
    summary.update({"success": True, "output": args.output,
                    "write": write_record,
                    "note": f"模型只替换 {PLACEHOLDER} 占位符与空容器；锁定字段禁改；填完后跑 verify_step"})
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
