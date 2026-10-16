# -*- coding: utf-8 -*-
"""
write_guard.py — 写入分类、路径守卫与覆盖守卫（本技能所有落盘脚本共用）

本技能每一次写盘都必须声明写入类型，四类语义固定：

| 类型 | 落盘位置 | 覆盖策略 |
| --- | --- | --- |
| `artifact` | `中间数据文件/market_share.json`、`representative_items.json`、`item_attributes.json`、`kano_final.json` | 下游消费产物与模型语义产物；目标已存在必须逐路径精确授权，覆盖前备份原件 |
| `cache` | 同输入可重取的临时结果 | 允许原子覆盖；本技能当前不产生此类写入 |
| `state` | 跨运行状态文件 | 与 `artifact` 同等守卫；本技能当前不产生此类写入 |
| `temporary` | `临时文件/` 下的备份与草稿 | 允许覆盖，随时可删 |

风险来源：`中间数据文件/` 是编排方共享目录（下游报告技能正在消费），同一 work_dir 重跑会
静默覆盖已被消费的 `market_share.json`；`build_skeleton.py --force` 与 `fill_attributes_fallback.py`
的原地填充会不可逆地覆盖模型已填内容。

所有写入统一走 `guarded_write`：路径守卫 → 覆盖授权 → 备份 → `.partial` 原子替换。
失败一律抛 `WriteGuardError`，由各脚本转为自身契约错误（退出码 2）。
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

ARTIFACT_TYPES = ("artifact", "cache", "state", "temporary")
# 需要逐路径显式授权才允许覆盖的类型（下游消费产物、模型语义产物、跨运行状态）
PROTECTED_TYPES = ("artifact", "state")
# 中间产物目录名：用于从产物路径反推 work_dir 边界
ARTIFACT_DIR_NAME = "中间数据文件"
BACKUP_DIR_NAME = "临时文件"


class WriteGuardError(Exception):
    """输出路径或覆盖授权不满足写入守卫。"""


# ---------------------------------------------------------------------------
# 路径守卫
# ---------------------------------------------------------------------------
def derive_base(candidate) -> Path:
    """从产物路径反推 work_dir 边界：`<work_dir>/中间数据文件/x.json` → `<work_dir>`。

    本技能脚本只接收具体文件路径（不接收 work_dir），备份需落在 work_dir 的
    `临时文件/` 而非共享的 `中间数据文件/`，故统一由此推导边界。
    """
    parent = Path(str(candidate)).expanduser().resolve().parent
    if parent.name == ARTIFACT_DIR_NAME:
        return parent.parent
    return parent


def safe_output_path(base: Path, candidate, label: str) -> Path:
    """校验调用方传入的输出路径，返回落在 base 内的路径。"""
    if candidate in (None, ""):
        raise WriteGuardError(f"{label} 不能为空")
    base = Path(base)
    raw = Path(str(candidate))
    if ".." in raw.parts:
        raise WriteGuardError(f"{label} 不得包含 .. 逃逸: {candidate}")
    target = raw if raw.is_absolute() else base / raw
    base_resolved = base.resolve()
    target_resolved = Path(os.path.normpath(str(target))).resolve()
    if base_resolved != target_resolved and base_resolved not in target_resolved.parents:
        raise WriteGuardError(
            f"{label} 必须写在 {base_resolved} 之内，拒绝越界路径: {target_resolved}")
    return target


def ensure_within(base: Path, target: Path, label: str) -> Path:
    """兜底校验：已构造好的写入目标必须仍在 base 之内。"""
    return safe_output_path(base, target, label)


def relative_label(base: Path, target: Path) -> str:
    """用于提示与授权比对的 base 相对路径。"""
    try:
        return Path(target).resolve().relative_to(Path(base).resolve()).as_posix()
    except ValueError:
        return str(target)


# ---------------------------------------------------------------------------
# 覆盖守卫
# ---------------------------------------------------------------------------
def is_authorized(base: Path, target: Path, allow_overwrite=()) -> bool:
    """覆盖授权必须逐路径精确匹配（base 相对路径或文件名），禁止整体放行。"""
    tokens = set()
    for item in allow_overwrite or ():
        text = str(item).strip().replace("\\", "/")
        if not text:
            continue
        tokens.add(text)
        tokens.add(Path(text).name)
    if not tokens:
        return False
    return bool({Path(target).name, relative_label(base, target)} & tokens)


def _backup(base: Path, target: Path, backup_dir=None) -> Path:
    root = Path(backup_dir) if backup_dir else Path(base) / BACKUP_DIR_NAME
    stamped = root / f"write-backup-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    backup = stamped / Path(target).name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    return backup


def guarded_write(target, text, base, artifact_type: str, label: str,
                  allow_overwrite=(), backup_dir=None) -> dict:
    """按写入类型执行路径守卫、覆盖授权、备份与原子替换；返回写入记录。"""
    if artifact_type not in ARTIFACT_TYPES:
        raise WriteGuardError(
            f"{label} 写入类型非法: {artifact_type!r}，必须是 {'/'.join(ARTIFACT_TYPES)}")
    base = Path(base)
    target = ensure_within(base, target, label=f"{label} 写入路径")
    relative = relative_label(base, target)
    if not target.parent.is_dir():
        raise WriteGuardError(f"{label} 目标目录不存在: {target.parent}")
    if not isinstance(text, str) or not text.strip():
        raise WriteGuardError(f"{label} 待写入内容为空: {relative}")
    if target.suffix == ".json":
        try:
            json.loads(text)
        except ValueError as exc:
            raise WriteGuardError(f"{label} 待写入 JSON 非法: {relative} → {exc}") from exc

    existed = target.exists()
    if existed and (target.is_symlink() or not target.is_file()):
        raise WriteGuardError(f"{label} 目标已存在且不是普通文件: {relative}")
    backup = None
    if existed and artifact_type in PROTECTED_TYPES:
        if not is_authorized(base, target, allow_overwrite):
            raise WriteGuardError(
                f"{label} 目标已存在且未获覆盖授权: {relative}；"
                f"请改用新的干净 work_dir，或显式精确授权 --allow-overwrite {relative}")
        backup = _backup(base, target, backup_dir)

    partial = target.with_name(target.name + ".partial")
    try:
        partial.write_text(text, encoding="utf-8")
        if partial.stat().st_size == 0:
            raise WriteGuardError(f"{label} 暂存文件落盘后为空: {relative}")
        if target.suffix == ".json":
            json.loads(partial.read_text(encoding="utf-8"))
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    return {
        "path": str(target),
        "relPath": relative,
        "artifactType": artifact_type,
        "action": "overwrite" if existed else "create",
        "backup": str(backup) if backup else None,
    }


def write_json(candidate, payload, artifact_type: str, label: str,
               allow_overwrite=()) -> dict:
    """JSON 产物落盘统一入口：推导 work_dir 边界 → 路径守卫 → guarded_write。"""
    base = derive_base(candidate)
    target = safe_output_path(base, candidate, label)
    target.parent.mkdir(parents=True, exist_ok=True)
    return guarded_write(
        target,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        base=base,
        artifact_type=artifact_type,
        label=label,
        allow_overwrite=allow_overwrite,
    )
