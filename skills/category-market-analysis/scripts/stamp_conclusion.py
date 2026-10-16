# -*- coding: utf-8 -*-
"""category-market-analysis 结论盖章器（生产方凭证，verify_step finalize 通过后调用）。

职责（对 market_share.json 原地增量，不改任何既有业务字段）：
1. 注入 meta 段：schemaVersion / producer / analyzedAt / inputs（采集缺口结构化透传：
   top_items 的 complete/truncatedReason/failedBands/totalItems + strategy 的 source/status）。
2. 写入 validation 凭证（payloadHash 排除 validation 自身）。
3. 写入统一走 write_guard（market_share.json 属 `artifact`）：盖章前先把原件备份到
   `临时文件/write-backup-*/`，再走 .partial 原子替换；备份路径进 stdout。
4. 重复盖章守卫：已带凭证的文件默认拒绝重盖，需显式 `--restamp` 确认。

前置：verify_step --step finalize 必须已通过（kano_final 均为 dict、representative_items 三维非空）。
用法：
    python3 stamp_conclusion.py --share <market_share.json> \
        --top-items <top_items_raw.json> --strategy <category_selling_point_strategy.json>
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import write_guard  # noqa: E402  写入分类 / 路径守卫 / 覆盖守卫

PRODUCER = "category-market-analysis"
SCHEMA_VERSION = "2"


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


def _payload_hash(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "validation"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="market_share.json 结论盖章")
    parser.add_argument("--share", required=True, help="market_share.json 路径（回灌后）")
    parser.add_argument("--top-items", required=True, help="top_items_raw.json 路径")
    parser.add_argument("--strategy", required=True, help="category_selling_point_strategy.json 路径")
    parser.add_argument("--restamp", action="store_true",
                        help="已带 validation 凭证的 market_share.json 默认拒绝重盖；确需重新盖章请显式传入"
                             "（不可逆：旧凭证会被覆盖，原件自动备份到 临时文件/write-backup-*/）")
    args = parser.parse_args()

    share = _load(args.share, "market_share.json")
    top = _load(args.top_items, "top_items_raw.json")
    strategy = _load(args.strategy, "category_selling_point_strategy.json")

    if not isinstance(share, dict) or not share.get("selling_point_share"):
        print("[FAIL] market_share.json 结构异常（缺 selling_point_share），先跑 verify_step --step finalize", file=sys.stderr)
        return 2
    # 锁定字段防篡改抽检：回灌后的 kano_final 必须是 dict
    for sp in share.get("selling_point_share", []):
        kf = sp.get("kano_final")
        if kf is not None and not isinstance(kf, dict):
            print(f"[FAIL] selling_point_share[{sp.get('selling_point')}].kano_final 不是 dict，禁止盖章", file=sys.stderr)
            return 2

    # 重复盖章守卫：旧凭证（validation.payloadHash）被覆写后无法恢复，需显式确认
    existing_validation = share.get("validation")
    if isinstance(existing_validation, dict) and existing_validation.get("payloadHash") and not args.restamp:
        print(f"[FAIL] market_share.json 已带 validation 凭证（validatedAt="
              f"{existing_validation.get('validatedAt')}），拒绝重复盖章；\n"
              f"       确需重新盖章请加 --restamp（覆盖前会把原件备份到 临时文件/write-backup-*/）",
              file=sys.stderr)
        return 2

    top_stats = top.get("stats") if isinstance(top.get("stats"), dict) else {}
    strategy_status = str(strategy.get("status") or "ready")
    # 降级信息必须透传给下游（报告需显式标注类目决策词不可用）
    strategy_degraded = (
        strategy_status in ("no_data", "unavailable") or strategy.get("degraded") is True
    )
    share["meta"] = {
        "schemaVersion": SCHEMA_VERSION,
        "producer": PRODUCER,
        "analyzedAt": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "topItems": {
                "file": os.path.basename(args.top_items),
                "totalItems": top_stats.get("totalItems", top.get("total_items")),
                "complete": top_stats.get("complete"),
                "truncatedReason": top_stats.get("truncatedReason"),
                "failedBands": top_stats.get("failedBands", []),
            },
            "strategy": {
                "file": os.path.basename(args.strategy),
                "source": strategy.get("source"),
                "status": strategy_status,
                "degraded": strategy_degraded,
                "degradeReason": strategy.get("degradeReason") or (
                    strategy_status if strategy_degraded else None
                ),
                "unavailableReason": strategy.get("unavailable_reason"),
                "fallbackMode": (strategy.get("fallback") or {}).get("mode")
                if isinstance(strategy.get("fallback"), dict) else None,
            },
        },
    }
    share["validation"] = {
        "status": "passed",
        "payloadHash": _payload_hash(share),
        "validatedAt": datetime.now().isoformat(timespec="seconds"),
        "validatorVersion": "1",
    }

    # 盖章是对本技能自有产物的设计内增量（⑥）：逐路径自授权，但必经守卫先备份原件再原子替换
    try:
        write_record = write_guard.write_json(
            args.share, share, artifact_type="artifact",
            label=os.path.basename(args.share),
            allow_overwrite=[os.path.basename(args.share)])
    except write_guard.WriteGuardError as exc:
        print(f"[FAIL] 写入被守卫拒绝: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "success": True,
        "share": args.share,
        "write": write_record,
        "inputsComplete": top_stats.get("complete"),
        "strategyStatus": strategy_status,
        "strategyDegraded": strategy_degraded,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
