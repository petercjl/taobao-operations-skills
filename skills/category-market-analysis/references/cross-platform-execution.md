> ⚠ 快照来源：skills/category-market-insight/references/cross-platform-execution.md（拆分迁移，2026-08-21）。原件仍被迁移期单体使用；修改时评估双向同步。

# 跨端脚本执行约定

本 Skill 的 Python 脚本在 Windows 与 macOS/Linux 使用同一参数和文件协议。Shell
只负责启动进程，不负责拼业务 JSON、工作目录或缓存目录。

## 选择运行方式

Windows PowerShell：

```powershell
$ParentSkillRoot = if ($env:AGENT_HUB_SKILL_DIR) {
  $env:AGENT_HUB_SKILL_DIR
} elseif ($env:SKILL_DIR) {
  $env:SKILL_DIR
} else {
  (Get-Location).Path
}
$Python = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
if (-not (Test-Path -LiteralPath (Join-Path $ParentSkillRoot "SKILL.md"))) {
  throw "Skill 根目录无效: $ParentSkillRoot"
}
```

macOS/Linux bash 或 zsh：

```bash
PARENT_SKILL_ROOT="${AGENT_HUB_SKILL_DIR:-${SKILL_DIR:-$PWD}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
test -s "$PARENT_SKILL_ROOT/SKILL.md"
```

调用脚本时始终把脚本路径和每个参数作为独立 argv，并引用可能含空格的路径：

```powershell
& $Python (Join-Path $ParentSkillRoot "scripts/validate_input.py") `
  --top-items $TopItems --strategy $Strategy
```

```bash
"$PYTHON_BIN" "$PARENT_SKILL_ROOT/scripts/validate_input.py" \
  --top-items "$TOP_ITEMS" --strategy "$STRATEGY"
```

## 数据和路径契约

- 以 `cateId` 作为稳定类目身份；`cateName`、`cateFullName` 只用于展示。
- `work_dir` 由编排方 init 后透传；不要根据类目名手工拼目录。
- 复杂或大 JSON 只通过 `--data-file`、`--request`、`--output` 或 stdin 传递。
- 不把 `Get-Content -Raw`、`$(cat ...)` 的文件内容展开进命令行参数。
- 不在 PowerShell 中复制 Bash heredoc（`<<EOF`），也不在 Bash/zsh 中复制
  PowerShell here-string。
- 临时文件放到当前任务的 `临时文件/` 或 Python `tempfile` 目录；不写死 `/tmp`
  或 Windows 用户目录。
- Python 内部启动子进程时使用 `sys.executable`、argv 列表和 `shell=False`。
- 不猜测底层 Shell 是 cmd、Git Bash 还是 PowerShell；当前工具声明为 PowerShell 时只写 PowerShell 语法。
- 不用 `python -c` 承载多行 Python 或多层引号；复杂逻辑放进 Skill 脚本。
- 不追加 `2>&1` 合并原生程序输出；stdout/stderr 会分别被重定向保留。

本文档中的两套 Shell 示例语义等价。其他 reference 中如仅展示 POSIX 换行符，
Windows 执行时按本页 PowerShell 模式逐参数传递，不改变业务参数或文件协议。
