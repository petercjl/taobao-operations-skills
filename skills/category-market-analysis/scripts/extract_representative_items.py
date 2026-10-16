# -*- coding: utf-8 -*-
# ⚠ 快照来源：skills/category-market-insight/scripts/extract_representative_items.py（拆分迁移，2026-08-21）。
# 原件仍被 category-market-insight（迁移期单体）使用；修改本文件时必须评估是否需双向同步。
"""
extract_representative_items.py — 从 top_items_raw + item_attributes + market_share
抽取按「价格带 / 品牌 / 卖点」三维度的代表性商品清单，落盘 representative_items.json。

设计动机：
  market_share.json 是聚合统计层（无具体商品列表，只有 head_item_ids 字符串数组）；
  Excel 的「重点商品清单 Top30」 sheet 才是商品级证据。
  模型写 .md 报告时若仅看 market_share.json，无法把"哪些具体商品代表了头部品牌/价格带/卖点"
  讲清楚。本脚本预筛"已选好"的代表商品，结构化喂给模型，让 .md 报告富含商品级证据。

输出结构（representative_items.json）：
{
  "generated_at": "...",
  "config": {"items_per_group": 6, "max_band_groups": 6, "max_brand_groups": 6, "max_sp_groups": 15},
  "by_band": [
    {"band": "0-135", "items": [<item>, ...]},
    ...
  ],
  "by_brand": [
    {"brand": "倍思", "share": {"item_count": 28, "item_share": 4.7, "pay_byr_cnt_share": 17.1}, "items": [...]},
    ...
  ],
  "by_selling_point": [
    {"selling_point": "大容量", "kano_layer": "期望型", "share": {"item_share": 57.2, "pay_byr_cnt_share": 73.8}, "items": [...]},
    ...
  ]
}

每个 <item> 字段（已扁平、已注入属性）：
  item_id / title / shop_title / band / brand / pay_byr_cnt_min / pay_byr_cnt_raw / uv
  / pict_url / detail_url / selling_points (前 5 个)

写入分类（见 write_guard.py）：representative_items.json 属 `artifact`（下游报告商品证据唯一来源），
目标已存在时必须 `--allow-overwrite 中间数据文件/representative_items.json` 精确授权，
覆盖前自动备份到 `临时文件/write-backup-*/`。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import write_guard  # noqa: E402  写入分类 / 路径守卫 / 覆盖守卫


def _guarded_write(path: Path, payload: Dict[str, Any], allow_overwrite: Sequence[str] = ()) -> Dict[str, Any]:
    """artifact 落盘：路径守卫 → 覆盖授权 → 备份 → .partial 原子替换。"""
    try:
        return write_guard.write_json(path, payload, artifact_type="artifact",
                                      label=Path(path).name,
                                      allow_overwrite=allow_overwrite)
    except write_guard.WriteGuardError as exc:
        print(f"ERROR: 写入被守卫拒绝: {exc}", file=sys.stderr)
        sys.exit(2)


# ───── schema 兼容层（与 generate_excel_report.py 保持一致）─────
def _band_list(share: Dict[str, Any]) -> List[Dict[str, Any]]:
    return share.get("band_share") or share.get("by_band") or []


def _brand_list(share: Dict[str, Any]) -> List[Dict[str, Any]]:
    return share.get("brand_share") or share.get("by_brand") or []


def _sp_list(share: Dict[str, Any]) -> List[Dict[str, Any]]:
    return share.get("selling_point_share") or share.get("by_selling_point") or []


def _final_layer(sp: Dict[str, Any]) -> Optional[str]:
    """优先取模型终判，未回灌时退回脚本 kano_layer。"""
    final = sp.get("kano_final")
    if isinstance(final, dict) and final.get("kano_layer"):
        return final.get("kano_layer")
    if isinstance(final, str) and final.strip():
        return final.strip()
    return sp.get("kano_layer")


def _to_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _build_attrs_index(attrs_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """item_attributes.json 顶层 items 是 list（每条含 itemId）— 转成 dict 方便查询。"""
    items = attrs_payload.get("items") or []
    if isinstance(items, dict):
        return {str(k): v for k, v in items.items()}
    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        iid = str(it.get("itemId") or it.get("item_id") or "")
        if iid:
            out[iid] = it
    return out


def _flatten_items(raw: Dict[str, Any], attrs_index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 raw.bands[].items[] 扁平化，并注入 brand / selling_points。"""
    flat: List[Dict[str, Any]] = []
    for band in raw.get("bands", []):
        band_label = band.get("band") or ""
        for it in band.get("items", []):
            iid = str(it.get("item_id") or "")
            attr = attrs_index.get(iid) or {}
            flat.append({
                "item_id": iid,
                "title": it.get("title") or "",
                "shop_title": it.get("shop_title") or "",
                "band": band_label,
                "brand": attr.get("brand") or "",
                "pay_byr_cnt_min": _to_int(it.get("pay_byr_cnt_min")),
                "pay_byr_cnt_raw": it.get("pay_byr_cnt_raw") or "",
                "uv": _to_int(it.get("uv")),
                "pict_url": it.get("pict_url") or "",
                "detail_url": it.get("detail_url") or f"https://item.taobao.com/item.htm?id={iid}",
                "selling_points": list((attr.get("selling_points") or [])[:5]),
            })
    flat.sort(key=lambda x: x.get("pay_byr_cnt_min") or 0, reverse=True)
    return flat


def _pick_by_band(flat: List[Dict[str, Any]], share: Dict[str, Any],
                  max_groups: int, items_per_group: int) -> List[Dict[str, Any]]:
    band_values: List[str] = []
    for b in _band_list(share):
        bn = b.get("band")
        if bn and bn not in band_values:
            band_values.append(bn)
    band_values = band_values[:max_groups]

    out: List[Dict[str, Any]] = []
    for bn in band_values:
        items = [it for it in flat if it.get("band") == bn][:items_per_group]
        if items:
            out.append({"band": bn, "items": items})
    return out


def _pick_by_brand(flat: List[Dict[str, Any]], share: Dict[str, Any],
                   max_groups: int, items_per_group: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for b in _brand_list(share)[:max_groups]:
        bn = b.get("brand") or ""
        if not bn:
            continue
        items = [it for it in flat if (it.get("brand") or "") == bn][:items_per_group]
        if not items:
            continue
        out.append({
            "brand": bn,
            "share": {
                "item_count": b.get("item_count"),
                "item_share": b.get("item_share"),
                "pay_byr_cnt_share": b.get("pay_byr_cnt_share"),
                "top_bands": b.get("top_bands") or [],
            },
            "items": items,
        })
    return out


def _pick_by_sp(flat: List[Dict[str, Any]], share: Dict[str, Any],
                max_groups: int, items_per_group: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sp in _sp_list(share)[:max_groups]:
        spn = sp.get("selling_point") or ""
        if not spn:
            continue
        items = [it for it in flat if spn in (it.get("selling_points") or [])][:items_per_group]
        if not items:
            continue
        out.append({
            "selling_point": spn,
            "kano_layer": _final_layer(sp),
            "share": {
                "item_share": sp.get("item_share"),
                "pay_byr_cnt_share": sp.get("pay_byr_cnt_share"),
                "top_concentration": sp.get("top_concentration"),
            },
            "items": items,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="抽取代表性商品清单（按价格带/品牌/卖点三维度）")
    ap.add_argument("--raw", required=True, help="top_items_raw.json 路径")
    ap.add_argument("--attrs", required=True, help="item_attributes.json 路径")
    ap.add_argument("--share", required=True, help="market_share.json 路径")
    ap.add_argument("--output", required=True, help="输出 representative_items.json 路径")
    ap.add_argument("--items-per-group", type=int, default=6,
                    help="每组保留的代表商品个数（默认 6）")
    ap.add_argument("--max-band-groups", type=int, default=6,
                    help="价格带分组个数（默认 6，即所有价格带）")
    ap.add_argument("--max-brand-groups", type=int, default=6,
                    help="品牌分组个数（默认 6，按品牌商品数倒序取）")
    ap.add_argument("--max-sp-groups", type=int, default=15,
                    help="卖点分组个数（默认 15，与 KANO 报告主轴卖点数对齐）")
    ap.add_argument("--allow-overwrite", action="append", default=[], metavar="REL_PATH",
                    help="逐路径精确授权覆盖已存在的 artifact 产物"
                         "（如 中间数据文件/representative_items.json）；覆盖前自动备份")
    args = ap.parse_args()

    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    attrs_payload = json.loads(Path(args.attrs).read_text(encoding="utf-8"))
    share = json.loads(Path(args.share).read_text(encoding="utf-8"))

    attrs_index = _build_attrs_index(attrs_payload)
    flat = _flatten_items(raw, attrs_index)

    if not flat:
        print("ERROR: top_items_raw.json 扁平化后为空，无法抽取代表商品", file=sys.stderr)
        sys.exit(1)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "items_per_group": args.items_per_group,
            "max_band_groups": args.max_band_groups,
            "max_brand_groups": args.max_brand_groups,
            "max_sp_groups": args.max_sp_groups,
            "total_flat_items": len(flat),
        },
        "by_band": _pick_by_band(flat, share, args.max_band_groups, args.items_per_group),
        "by_brand": _pick_by_brand(flat, share, args.max_brand_groups, args.items_per_group),
        "by_selling_point": _pick_by_sp(flat, share, args.max_sp_groups, args.items_per_group),
    }

    out_path = Path(args.output)
    write_record = _guarded_write(out_path, payload, allow_overwrite=args.allow_overwrite)

    print(f"✅ representative_items.json 已生成：{out_path}（{write_record['action']}"
          + (f"，原件备份={write_record['backup']}" if write_record.get("backup") else "") + "）")
    print(f"   by_band={len(payload['by_band'])} 组 | "
          f"by_brand={len(payload['by_brand'])} 组 | "
          f"by_selling_point={len(payload['by_selling_point'])} 组 | "
          f"items_per_group={args.items_per_group}")


if __name__ == "__main__":
    main()
