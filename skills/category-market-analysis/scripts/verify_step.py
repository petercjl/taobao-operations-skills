# -*- coding: utf-8 -*-
# ⚠ 快照来源：skills/category-market-insight/scripts/verify_step.py（拆分迁移，2026-08-21）。
# 原件仍被 category-market-insight（迁移期单体）使用；修改本文件时必须评估是否需双向同步。
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
category-market-insight 步骤级自检脚本（A 档加固）。

设计目标：在「模型决策点 / pipeline phase 切换」的关键节点拦下 schema/字段错，
避免错误数据进入下一步污染 KANO 终判 / Excel / HTML / md 报告。
失败时打印 retry_commands + 修复闭环 4 步，退出码 ≠0 时当前 todo 项不得标记为完成。

支持 step：
  --step Step3b    校验依赖文件协议产出的 category_selling_point_strategy.json
  --step Step3c    模型产出 中间数据文件/item_attributes.json 后立即跑
                   （items[] 非空、卖点-来源标记一致、selling_point_origins 取值合法）
  --step Step4b    模型产出 中间数据文件/kano_final.json 后立即跑
                   （selling_points[] 非空、kano_final 是 dict 而非字符串、kano_layer 合法值、override_reason 在 disagree 时非空）
  --step finalize  pipeline finalize 完成后跑
                   （market_share.json kano 已回灌成 dict、representative_items.json 三维度非空）
  --step C7.1      交付前最后一道总检（mark-completed 之前），三件套齐全 + market_share kano 校验 + preflight 关键字段
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


VALID_KANO_LAYERS = {"基础型", "期望型", "兴奋型", "无差异型"}
VALID_ORIGIN = {"authority", "reference_md"}
SCRIPT_ROOT = Path(__file__).resolve().parent


def _print_banner(title: str) -> None:
    bar = "=" * 64
    print(bar)
    print(title)
    print(bar)


def _print_recovery_loop(retry_commands: List[str]) -> None:
    print("修复闭环 4 步（必须全部走完才能 COMPLETE 当前 todo 项）:")
    print("  ① 定位失败字段：阅读上方 [FAIL] 错误信息，明确具体哪个字段/文件出错（不靠猜）")
    print("  ② 增量修复：只改失败字段，禁止全量覆写文件丢失原有正确字段")
    print("  ③ 按下面 retry_commands 顺序重跑（不允许只跑 verify_step 跳过下游 phase 脚本）：")
    if retry_commands:
        for i, cmd in enumerate(retry_commands, 1):
            print(f"       {i}) {cmd}")
    else:
        print("       （本步无下游 phase，仅需重跑 verify_step）")
    print("  ④ retry 链路全部退出码 0 后，方可把当前 todo 项从 IN_PROGRESS 转 COMPLETE")


def _fail(step: str, label: str, errors: List[str], fix_hint: str, retry_commands: List[str]) -> None:
    _print_banner(f"[FAIL] 步骤 {step} 自检未通过：{label}")
    for e in errors:
        print(f"  ✗ {e}")
    print("修复指引：")
    for line in fix_hint.strip().splitlines():
        print(f"  {line}")
    _print_recovery_loop(retry_commands)
    print("=" * 64)
    sys.exit(2)


def _ok(step: str, label: str, infos: List[str]) -> None:
    _print_banner(f"[PASS] 步骤 {step} 自检通过：{label}")
    for i in infos:
        print(f"  ✓ {i}")
    print("=" * 64)


def _load_json(path: Path) -> Tuple[Any, List[str]]:
    if not path.exists():
        return None, [f"文件不存在: {path}"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as e:
        return None, [f"JSON 解析失败: {path} → {e}"]


# ---------------------------------------------------------------------------
# Step3b: category_selling_point_strategy.json 依赖文件协议
# ---------------------------------------------------------------------------
def verify_step3b(work_dir: Path) -> None:
    label = "Step3b 依赖文件协议输出 + 富结构 consumer_decision_factors"
    middle_dir = work_dir / "中间数据文件"
    output_path = middle_dir / "category_selling_point_strategy.json"
    request_path = middle_dir / "category_decision_request.json"
    retry = [
        "# Step3b 失败说明上游卖点策略文件不合格。交回编排层，让 category-top-items-fetch 重新产出该文件后重跑：",
        f'python3 "{SCRIPT_ROOT / "validate_input.py"}" --top-items <top_items_raw.json> --strategy <category_selling_point_strategy.json>',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step Step3b --work-dir "{work_dir}"',
        "# 若取数侧决策属性依赖失败（ATP 超时/权限/协议/JSON 解析失败），由取数技能落降级契约而不是卡死：",
        'python3 "<category-top-items-fetch>/scripts/strategy_handoff.py" degrade '
        f'--work-dir "{work_dir}" --reason "<真实失败原因>"',
    ]
    fix = (
        "Step3b 校验失败。请交回编排层，由 category-top-items-fetch 重新产出卖点策略文件。\n"
        "- 不得从依赖回复正文构造业务 JSON\n"
        "- 不得扫描 cwd 或复用其他任务文件\n"
        "- 不得手写 placeholder/unavailable_reason 文件冒充结果\n"
        "- 本技能不写降级契约：取数侧依赖失败时由 strategy_handoff.py degrade 落 status=unavailable，不要卡在本步"
    )

    data, errors = _load_json(output_path)
    if errors:
        _fail("Step3b", label, errors, fix, retry)
    if not isinstance(data, dict):
        _fail("Step3b", label, ["输出顶层不是 object"], fix, retry)

    errors = []
    # 合法降级出口（均不阻断，标注后继续 Step3c）：
    #   degradeReason=no_data           依赖可达但类目确无决策属性（依赖返回的权威空结果）
    #   degradeReason=dependency_failed 取数侧依赖执行失败（由 category-top-items-fetch 的 strategy_handoff.py degrade 落盘）
    is_degraded = (
        str(data.get("status") or "") in ("no_data", "unavailable")
        or data.get("degraded") is True
    )
    degrade_reason = str(data.get("degradeReason") or ("no_data" if is_degraded else ""))
    if not is_degraded and (data.get("unavailable_reason") or data.get("source") == "placeholder"):
        errors.append("依赖输出是手写占位或不可用状态，且未带降级协议标记，必须修复 Step3b")
    if data.get("schemaVersion") != 1:
        errors.append("schemaVersion 必须为 1")
    if data.get("mode") != "category_decision_factors":
        errors.append("mode 必须为 category_decision_factors")
    if data.get("source") not in ("category-decision-factor-fetch", "item-selling-point-alg-strategy"):
        errors.append("source 必须为 category-decision-factor-fetch（迁移期兼容 item-selling-point-alg-strategy）")
    if "status" in data and data.get("status") not in ("ready", "no_data", "unavailable"):
        errors.append("status 必须 ∈ {ready, no_data, unavailable}")
    if degrade_reason == "dependency_failed":
        if not str(data.get("unavailable_reason") or "").strip():
            errors.append("dependency_failed 降级必须写 unavailable_reason（真实失败原因）")
        # attempts 只记录真实尝试次数（取数侧首次失败即可降级），故最小值为 1，不强制重试
        if int(data.get("attempts") or 0) < 1:
            errors.append("dependency_failed 降级必须写 attempts（真实尝试次数，最小 1）")
    if not data.get("requestId"):
        errors.append("缺少 requestId")
    if not (data.get("category_id") or data.get("cateId")):
        errors.append("缺少 category_id")
    if request_path.exists():
        request, request_errors = _load_json(request_path)
        errors.extend(request_errors)
        if isinstance(request, dict):
            if data.get("requestId") != request.get("requestId"):
                errors.append("output.requestId 与当前 request 不一致")
            if str(data.get("category_id") or data.get("cateId") or "") != str(
                request.get("cateId") or ""
            ):
                errors.append("output.category_id 与当前 request.cateId 不一致")

    cdf = data.get("consumer_decision_factors")
    if not isinstance(cdf, dict):
        errors.append("缺少 consumer_decision_factors 对象")
    else:
        has_valid_attribute = False
        diagnostics = []
        for scene_name in ("search", "purchase"):
            scene = cdf.get(scene_name)
            if not isinstance(scene, dict):
                errors.append(f"{scene_name} 必须为对象")
                continue
            if not isinstance(scene.get("success"), bool):
                errors.append(f"{scene_name}.success 必须为布尔值")
            scene_data = scene.get("data")
            result_list = (
                scene_data.get("result") if isinstance(scene_data, dict) else None
            )
            if not isinstance(result_list, list):
                errors.append(f"{scene_name}.data.result 必须为数组")
                continue
            if not result_list:
                diagnostics.append(f"{scene_name} 为空")
                continue
            for index, row in enumerate(result_list):
                if not isinstance(row, dict):
                    continue
                if not row.get("pname"):
                    errors.append(
                        f"{scene_name}.result[{index}] 缺少 pname"
                    )
                    continue
                if "std_score_p" not in row:
                    errors.append(
                        f"{scene_name}.result[{index}] 缺少 std_score_p"
                    )
                    continue
                if not row.get("v_list"):
                    errors.append(
                        f"{scene_name}.result[{index}] 缺少非空 v_list"
                    )
                    continue
                has_valid_attribute = True
        if not has_valid_attribute and not is_degraded:
            errors.append("search/purchase 均无合格属性项")
            errors.extend(f"  - {item}" for item in diagnostics[:8])

    if errors:
        _fail("Step3b", label, errors, fix, retry)

    if is_degraded:
        if degrade_reason == "dependency_failed":
            note = (
                "status=unavailable：依赖已尝试 %s 次仍失败（%s），按 dependency_failed 降级"
                % (data.get("attempts") or "-", (data.get("unavailable_reason") or "-")[:80])
            )
        else:
            note = "status=no_data：类目无权威决策属性，后续 KANO 仅用脚本初判（已降级，非错误）"
        _ok(
            "Step3b",
            label + f"（降级：{degrade_reason or 'no_data'}）",
            [
                f"依赖输出: {output_path}",
                f"source: {data.get('source')}",
                f"category_id: {data.get('category_id') or data.get('cateId')}",
                note,
                "卖点提取改走 references/category-decision-attributes.md 关键词表兜底，"
                "item_attributes.json 必须写 _warnings 记录降级原因",
            ],
        )
        return

    _ok(
        "Step3b",
        label,
        [
            f"依赖输出: {output_path}",
            f"source: {data.get('source')}",
            f"category_id: {data.get('category_id') or data.get('cateId')}",
            "consumer_decision_factors 富结构有效",
        ],
    )

# ---------------------------------------------------------------------------
# Step3c: item_attributes.json
# ---------------------------------------------------------------------------
def verify_step3c(work_dir: Path) -> None:
    label = "Step3c item_attributes.json schema + 卖点-来源标记一致性"
    fp = work_dir / "中间数据文件" / "item_attributes.json"
    fp_strategy = work_dir / "中间数据文件" / "category_selling_point_strategy.json"

    retry = [
        f'# Step3c 是模型推理产物。修正后重跑 verify_step：',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step Step3c --work-dir "{work_dir}"',
        f'# Step3c 通过后，必须重跑占比计算让 market_share 反映新的卖点提取（覆盖已有 artifact 需精确授权，覆盖前自动备份）：',
        f'python3 "{SCRIPT_ROOT / "analyze_market_share.py"}" --raw <top_items_raw.json> --attrs <item_attributes.json> --out <market_share.json> --strategy <category_selling_point_strategy.json> --allow-overwrite 中间数据文件/market_share.json',
        f'# 然后回 Step4b 重做 KANO 终判（脚本初判变了模型也要重判）：',
        f'# 模型按 references/schemas.md kano_final.json 重写',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step Step4b --work-dir "{work_dir}"',
    ]
    fix = (
        "Step3c 模型产出异常。请检查：\n"
        "- items[] 是否存在且非空\n"
        "- 每条 itemId / band / brand / selling_points(数组) / selling_point_categories(对象) / selling_point_origins(对象) / kano_layer 是否齐全\n"
        "- selling_points 中每个卖点必须在 selling_point_origins 中有键\n"
        "- selling_point_origins 取值必须 ∈ {authority, reference_md}\n"
        "- category_selling_point_strategy.json 必须是已通过 Step3b 的规范依赖输出\n"
        "- 依赖输出非空时，authority 命中率应 ≥30%（详见 references/selling-point-extraction.md）\n"
        "- 依赖处于降级态（status=no_data / unavailable）时，_warnings 必须记录降级原因，"
        "卖点全部走 reference_md 兜底"
    )

    data, errs = _load_json(fp)
    if errs:
        _fail("Step3c", label, errs, fix, retry)

    errors: List[str] = []
    if not isinstance(data, dict):
        _fail("Step3c", label, ["顶层不是 object"], fix, retry)

    # 骨架填空纪律：占位符必须全部填完（build_skeleton.py 预填的 <待填>）
    if "<待填>" in fp.read_text(encoding="utf-8"):
        errors.append("存在未填完的 <待填> 占位符（骨架填空未完成，禁止交付半成品）")

    for f in ("authority_source", "items"):
        if f not in data:
            errors.append(f"顶层缺字段: {f}")

    items = data.get("items")
    if not isinstance(items, list) or len(items) == 0:
        _fail("Step3c", label, errors + ["items 不存在或为空"], fix, retry)

    strategy_data, strategy_errors = _load_json(fp_strategy)
    errors.extend(strategy_errors)
    # is_degraded：strategy 处于协议降级态（status=no_data 权威空结果 / status=unavailable
    # 取数侧没取到决策属性）。降级态下 item_attributes 允许全部走 reference_md 兜底，不校验
    # authority 命中率，也不把「无有效权威信号」当致命错误；但必须写 _warnings 留痕。
    is_degraded = False
    degrade_reason = ""
    if isinstance(strategy_data, dict):
        status = str(strategy_data.get("status") or "")
        is_degraded = status in ("no_data", "unavailable") or strategy_data.get("degraded") is True
        degrade_reason = str(strategy_data.get("degradeReason") or (status if is_degraded else ""))
        if not is_degraded and (
            strategy_data.get("source") == "placeholder"
            or strategy_data.get("unavailable_reason")
        ):
            errors.append(
                "category_selling_point_strategy.json 是手写占位或不可用状态且未带降级协议标记，"
                "必须先修复 Step3b"
            )
        # 权威信号有效性：cdf 富结构（category-decision-factor-fetch 主形态）或 selling_point_strategy（兼容简化形态）至少一侧非空
        _cdf = strategy_data.get("consumer_decision_factors") or {}
        _cdf_has_attr = any(
            isinstance(((_cdf.get(k) or {}).get("data") or {}), dict)
            and ((_cdf.get(k) or {}).get("data") or {}).get("result")
            for k in ("search", "purchase")
        )
        if not _cdf_has_attr and not strategy_data.get("selling_point_strategy"):
            # 仅在非降级态才视为致命：ready 却无权威信号说明取数异常；降级态属正常出口
            if not is_degraded:
                errors.append("category_selling_point_strategy.json 无有效权威信号（cdf 富结构与 selling_point_strategy 均为空）")

    # 降级态留痕义务：_warnings 必须显式记录降级原因，避免报告读者误当权威结论
    if is_degraded:
        warnings = data.get("_warnings")
        if not isinstance(warnings, list) or not [w for w in warnings if str(w).strip()]:
            errors.append(
                f"依赖处于降级态（{degrade_reason or 'degraded'}），item_attributes.json 顶层"
                "_warnings 必须为非空数组并记录降级原因"
            )

    # 字段抽检 + 一致性
    MAX = 12
    missing_field_samples: List[str] = []
    invalid_origin_samples: List[str] = []
    sp_origin_mismatch: List[str] = []
    authority_hits = 0
    total_origins = 0

    for i, it in enumerate(items):
        if not isinstance(it, dict):
            errors.append(f"items[{i}] 不是 object")
            continue
        itid = str(it.get("itemId") or f"<index {i}>")
        for f in ("itemId", "band", "brand", "selling_points", "selling_point_categories", "selling_point_origins", "kano_layer"):
            if f not in it:
                missing_field_samples.append(f"items[{i}](itemId={itid}).{f} 缺失")

        sps = it.get("selling_points")
        spo = it.get("selling_point_origins")
        if not isinstance(sps, list):
            missing_field_samples.append(f"items[{i}](itemId={itid}).selling_points 不是数组")
            continue
        if not isinstance(spo, dict):
            missing_field_samples.append(f"items[{i}](itemId={itid}).selling_point_origins 不是 object")
            continue

        # selling_points 与 selling_point_origins 键集合一致
        for sp in sps:
            if sp not in spo:
                sp_origin_mismatch.append(
                    f"items[{i}](itemId={itid}) 卖点 {sp!r} 出现在 selling_points 但 selling_point_origins 中无该键"
                )
        for k, v in spo.items():
            total_origins += 1
            if v not in VALID_ORIGIN:
                invalid_origin_samples.append(
                    f"items[{i}](itemId={itid}).selling_point_origins[{k!r}]={v!r} 不在 {sorted(VALID_ORIGIN)}"
                )
            if v == "authority":
                authority_hits += 1

    for s in missing_field_samples[:MAX]:
        errors.append(s)
    if len(missing_field_samples) > MAX:
        errors.append(f"……另有 {len(missing_field_samples) - MAX} 条字段缺失（已截断）")
    for s in sp_origin_mismatch[:MAX]:
        errors.append(s)
    if len(sp_origin_mismatch) > MAX:
        errors.append(f"……另有 {len(sp_origin_mismatch) - MAX} 条卖点-来源键不一致（已截断）")
    for s in invalid_origin_samples[:MAX]:
        errors.append(s)
    if len(invalid_origin_samples) > MAX:
        errors.append(f"……另有 {len(invalid_origin_samples) - MAX} 条 origins 取值非法（已截断）")

    # 权威词表非空时 authority 命中率提示（warning 级别，不直接 fail）
    auth_warning = ""
    if not is_degraded and total_origins > 0:
        rate = authority_hits / total_origins
        if rate < 0.30:
            auth_warning = f"⚠️ 权威词表非占位，但 authority 命中率仅 {rate:.1%} < 30%，请审视卖点提取（详见 selling-point-extraction.md）"

    if errors:
        _fail("Step3c", label, errors, fix, retry)

    infos = [
        f"items 数量: {len(items)}",
        f"authority_source: {data.get('authority_source')}",
        f"依赖降级态: {degrade_reason or '否'}",
        f"authority 命中率: {authority_hits}/{total_origins}" if total_origins else "无 origins 记录",
    ]
    if auth_warning:
        infos.append(auth_warning)
    _ok("Step3c", label, infos)


# ---------------------------------------------------------------------------
# Step4b: kano_final.json
# ---------------------------------------------------------------------------
def verify_step4b(work_dir: Path) -> None:
    label = "Step4b kano_final.json schema + kano_final 必须 dict + override_reason 一致性"
    fp = work_dir / "中间数据文件" / "kano_final.json"

    retry = [
        f'# Step4b 是模型 KANO 终判产物。修正后重跑 verify_step：',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step Step4b --work-dir "{work_dir}"',
        f'# Step4b 通过后必须重跑回灌 + 代表商品预筛，让 kano 回灌到 market_share.json：',
        f'python3 "{SCRIPT_ROOT / "analyze_market_share.py"}" --share <market_share.json> --merge-kano-final <kano_final.json>',
        f'python3 "{SCRIPT_ROOT / "extract_representative_items.py"}" --raw <top_items_raw.json> --attrs <item_attributes.json> --share <market_share.json> --output <representative_items.json> --allow-overwrite 中间数据文件/representative_items.json',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step finalize --work-dir "{work_dir}"',
    ]
    fix = (
        "Step4b 模型产出异常。请检查：\n"
        "- selling_points[] 是否存在且非空\n"
        "- 每条 kano_final 必须是 dict（不允许字符串），含 kano_layer/agree_with_rule/override_reason/confidence\n"
        "- kano_layer 取值必须 ∈ {基础型, 期望型, 兴奋型, 无差异型}\n"
        "- agree_with_rule=false 时 override_reason 必须非空且含具体证据\n"
        "- confidence ∈ [0,1]\n"
        "- is_core_factor=true 的卖点初判 R0/R4 时不允许判为无差异型"
    )

    data, errs = _load_json(fp)
    if errs:
        _fail("Step4b", label, errs, fix, retry)

    errors: List[str] = []
    if not isinstance(data, dict):
        _fail("Step4b", label, ["顶层不是 object"], fix, retry)

    # 骨架填空纪律：占位符必须全部填完（build_skeleton.py 预填的 <待填>）
    if "<待填>" in fp.read_text(encoding="utf-8"):
        errors.append("存在未填完的 <待填> 占位符（骨架填空未完成，禁止交付半成品）")

    sps = data.get("selling_points")
    if not isinstance(sps, list) or len(sps) == 0:
        _fail("Step4b", label, ["selling_points 不存在或为空"], fix, retry)

    MAX = 15
    str_kano_samples: List[str] = []
    invalid_layer_samples: List[str] = []
    missing_reason_samples: List[str] = []
    invalid_conf_samples: List[str] = []
    missing_field_samples: List[str] = []

    for i, sp in enumerate(sps):
        if not isinstance(sp, dict):
            errors.append(f"selling_points[{i}] 不是 object")
            continue
        spname = str(sp.get("selling_point") or f"<index {i}>")
        kf = sp.get("kano_final")
        if not isinstance(kf, dict):
            str_kano_samples.append(
                f"selling_points[{i}](selling_point={spname!r}).kano_final 必须是 dict，但拿到 {type(kf).__name__}: {kf!r}"
            )
            continue
        layer = kf.get("kano_layer")
        if layer not in VALID_KANO_LAYERS:
            invalid_layer_samples.append(
                f"selling_points[{i}](selling_point={spname!r}).kano_final.kano_layer={layer!r} 不在 {sorted(VALID_KANO_LAYERS)}"
            )
        if "agree_with_rule" not in kf:
            missing_field_samples.append(
                f"selling_points[{i}](selling_point={spname!r}).kano_final.agree_with_rule 缺失"
            )
        else:
            if kf["agree_with_rule"] is False:
                reason = kf.get("override_reason")
                if not isinstance(reason, str) or not reason.strip():
                    missing_reason_samples.append(
                        f"selling_points[{i}](selling_point={spname!r}) agree_with_rule=false 但 override_reason 缺失或空"
                    )
        conf = kf.get("confidence")
        if conf is None or not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            invalid_conf_samples.append(
                f"selling_points[{i}](selling_point={spname!r}).kano_final.confidence={conf!r} 不在 [0,1]"
            )

    for bucket, name in [
        (str_kano_samples, "kano_final 不是 dict"),
        (invalid_layer_samples, "kano_layer 非法"),
        (missing_reason_samples, "override_reason 缺失"),
        (invalid_conf_samples, "confidence 非法"),
        (missing_field_samples, "字段缺失"),
    ]:
        for s in bucket[:MAX]:
            errors.append(s)
        if len(bucket) > MAX:
            errors.append(f"……另有 {len(bucket) - MAX} 条 {name}（已截断）")

    if errors:
        _fail("Step4b", label, errors, fix, retry)

    _ok(
        "Step4b",
        label,
        [
            f"selling_points 数量: {len(sps)}",
            f"全部 kano_final 都是 dict",
            f"全部 kano_layer 在合法集 {sorted(VALID_KANO_LAYERS)} 内",
        ],
    )


# ---------------------------------------------------------------------------
# finalize: market_share.json kano 回灌后 + representative_items.json 三维度
# ---------------------------------------------------------------------------
def verify_finalize(work_dir: Path) -> None:
    label = "finalize 后 market_share.json kano 回灌 + representative_items.json 三维度"
    fp_share = work_dir / "中间数据文件" / "market_share.json"
    fp_rep = work_dir / "中间数据文件" / "representative_items.json"

    retry = [
        f'# finalize 异常通常是 Step4b 没有正确写入 kano_final.json 导致回灌失败。先修 Step4b：',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step Step4b --work-dir "{work_dir}"',
        f'# 然后重跑回灌 + 代表商品预筛：',
        f'python3 "{SCRIPT_ROOT / "analyze_market_share.py"}" --share <market_share.json> --merge-kano-final <kano_final.json>',
        f'python3 "{SCRIPT_ROOT / "extract_representative_items.py"}" --raw <top_items_raw.json> --attrs <item_attributes.json> --share <market_share.json> --output <representative_items.json> --allow-overwrite 中间数据文件/representative_items.json',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step finalize --work-dir "{work_dir}"',
    ]
    fix = (
        "finalize 阶段产物异常。请检查：\n"
        "- market_share.json 是否含 selling_point_share[]，且每条 kano_final 必须是 dict（不能字符串）\n"
        "- selling_point_share[].kano_layer 必须在 {基础型, 期望型, 兴奋型, 无差异型}\n"
        "- representative_items.json 是否含 by_brand / by_selling_point / by_band 三个维度且均非空（每个维度至少 1 条且 items[] 非空）"
    )

    errors: List[str] = []

    share, errs1 = _load_json(fp_share)
    if errs1:
        _fail("finalize", label, errs1, fix, retry)
    if not isinstance(share, dict):
        _fail("finalize", label, ["market_share.json 顶层不是 object"], fix, retry)

    sp_share = share.get("selling_point_share")
    if not isinstance(sp_share, list) or len(sp_share) == 0:
        errors.append("market_share.selling_point_share 不存在或为空")
    else:
        for i, sp in enumerate(sp_share):
            if not isinstance(sp, dict):
                errors.append(f"selling_point_share[{i}] 不是 object")
                continue
            spname = sp.get("selling_point", f"<{i}>")
            kf = sp.get("kano_final")
            if kf is None:
                errors.append(f"selling_point_share[{i}](selling_point={spname!r}).kano_final 缺失（Step4b 未回灌成功）")
                continue
            if not isinstance(kf, dict):
                errors.append(
                    f"selling_point_share[{i}](selling_point={spname!r}).kano_final 必须是 dict，但拿到 {type(kf).__name__}（generate_excel_report 会直接 crash）"
                )
                continue
            layer = sp.get("kano_layer") or kf.get("kano_layer")
            if layer not in VALID_KANO_LAYERS:
                errors.append(
                    f"selling_point_share[{i}](selling_point={spname!r}).kano_layer={layer!r} 不在 {sorted(VALID_KANO_LAYERS)}"
                )

    rep, errs2 = _load_json(fp_rep)
    if errs2:
        errors.extend(errs2)
    elif not isinstance(rep, dict):
        errors.append("representative_items.json 顶层不是 object")
    else:
        for dim in ("by_brand", "by_selling_point", "by_band"):
            v = rep.get(dim)
            if not isinstance(v, list) or len(v) == 0:
                errors.append(f"representative_items.{dim} 不存在或为空（md 报告三表会缺数据）")
                continue
            empty_groups = []
            for j, group in enumerate(v):
                if not isinstance(group, dict):
                    errors.append(f"representative_items.{dim}[{j}] 不是 object")
                    continue
                its = group.get("items")
                if not isinstance(its, list) or len(its) == 0:
                    empty_groups.append(group.get(dim.replace("by_", "")) or f"<index {j}>")
            if empty_groups:
                errors.append(f"representative_items.{dim} 中以下组的 items[] 为空: {empty_groups}")

    if errors:
        _fail("finalize", label, errors, fix, retry)

    _ok(
        "finalize",
        label,
        [
            f"selling_point_share 数量: {len(sp_share)}",
            f"全部 kano_final 都是 dict + kano_layer 合法",
            f"representative_items 三维度均非空（by_brand/by_selling_point/by_band）",
        ],
    )


# ---------------------------------------------------------------------------
# C7.1: 交付前最终自检（mark-completed 之前）
# ---------------------------------------------------------------------------
def verify_c71(work_dir: Path) -> None:
    label = "C7.1 交付前总检：三件套齐全 + market_share kano 合规 + pipeline_meta status"
    deliv_dir = work_dir / "交付文件"

    retry = [
        f'# C7.1 失败通常是某件交付物缺失或 finalize 没有跑完整。按以下顺序补：',
        f'# 1) 若 .md 缺失：模型按 references/report-templates.md 写入 交付文件/品类市场洞察报告_*.md',
        f'# 2) 若 .html / .xlsx 缺失：',
        f'python3 "{SCRIPT_ROOT / "run_pipeline.py"}" --phase finalize --work-dir "{work_dir}"',
        f'# 3) 重新跑 verify_step finalize + C7.1 双自检：',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step finalize --work-dir "{work_dir}"',
        f'python3 "{SCRIPT_ROOT / "verify_step.py"}" --step C7.1 --work-dir "{work_dir}"',
        f'# 4) 三件套齐全且自检通过后，调 mark-completed 回写 status：',
        f'python3 "{SCRIPT_ROOT / "run_pipeline.py"}" --phase mark-completed --work-dir "{work_dir}"',
    ]
    fix = (
        "C7.1 交付前总检失败。请检查：\n"
        "- 交付文件/ 下三件套：品类市场洞察报告_*.md + 品类市场洞察可视化_*.html + 品类top100商品明细_*.xlsx\n"
        "- 中间数据文件/market_share.json 已通过 finalize 回灌（kano_final 都是 dict）\n"
        "- pipeline_meta.json 存在；status 当前应该 != 'completed'（mark-completed 会写入；若已是 completed 表示已完成无需再 verify）"
    )

    errors: List[str] = []

    if not deliv_dir.exists():
        _fail("C7.1", label, [f"交付目录不存在: {deliv_dir}"], fix, retry)

    md_files = list(deliv_dir.glob("品类市场洞察报告_*.md"))
    html_files = list(deliv_dir.glob("品类市场洞察可视化_*.html"))
    xlsx_files = list(deliv_dir.glob("品类top100商品明细_*.xlsx"))

    if not md_files:
        errors.append(f"交付文件/品类市场洞察报告_*.md 缺失（Step5a 未写入磁盘）")
    if not html_files:
        errors.append(f"交付文件/品类市场洞察可视化_*.html 缺失（finalize 未生成）")
    if not xlsx_files:
        errors.append(f"交付文件/品类top100商品明细_*.xlsx 缺失（finalize 未生成）")

    # md 文件大小不能为 0
    for f in md_files:
        if f.stat().st_size < 200:
            errors.append(f"{f.name} 大小 {f.stat().st_size} 字节 < 200，疑似空文件或仅占位")

    # market_share kano 合规复核
    fp_share = work_dir / "中间数据文件" / "market_share.json"
    share, errs1 = _load_json(fp_share)
    if errs1:
        errors.extend(errs1)
    elif isinstance(share, dict):
        sp_share = share.get("selling_point_share") or []
        bad = 0
        for sp in sp_share:
            if isinstance(sp, dict) and not isinstance(sp.get("kano_final"), dict):
                bad += 1
        if bad:
            errors.append(f"market_share.selling_point_share 仍有 {bad} 条 kano_final 不是 dict（generate_excel_report 会 crash）")

    # pipeline_meta 文件存在
    fp_meta = work_dir / "中间数据文件" / "pipeline_meta.json"
    if not fp_meta.exists():
        errors.append(f"pipeline_meta.json 缺失（init phase 没正常完成）")
    else:
        meta, _ = _load_json(fp_meta)
        if isinstance(meta, dict):
            status = meta.get("status")
            if status == "completed":
                # 仅给出 info，不视为错
                pass

    if errors:
        _fail("C7.1", label, errors, fix, retry)

    _ok(
        "C7.1",
        label,
        [
            f"三件套齐全：md={len(md_files)} / html={len(html_files)} / xlsx={len(xlsx_files)}",
            f"market_share.selling_point_share 全部 kano_final 是 dict",
            f"pipeline_meta.json 存在",
            f'下一步可调用：python3 "{SCRIPT_ROOT / "run_pipeline.py"}" --phase mark-completed --work-dir "{work_dir}"',
        ],
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
STEP_REGISTRY = {
    "Step3b": verify_step3b,
    "Step3c": verify_step3c,
    "Step4b": verify_step4b,
    "finalize": verify_finalize,
    # C7.1 交付总检属于 category-insight-report（生成技能），本技能不暴露
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="category-market-insight 步骤级自检（A 档加固版）"
    )
    parser.add_argument(
        "--step",
        required=True,
        choices=sorted(STEP_REGISTRY.keys()),
        help="要校验的步骤（Step3b/Step3c/Step4b/finalize/C7.1）",
    )
    parser.add_argument(
        "--work-dir",
        required=True,
        help="任务工作目录（含 中间数据文件/ + 交付文件/ 子目录）",
    )
    args = parser.parse_args()

    work_dir = Path(args.work_dir).expanduser()
    if not work_dir.exists():
        print(f"[ERROR] 工作目录不存在: {work_dir}")
        sys.exit(1)

    fn = STEP_REGISTRY[args.step]
    fn(work_dir)


if __name__ == "__main__":
    main()
