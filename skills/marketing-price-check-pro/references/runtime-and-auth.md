# 运行环境与鉴权

仅在 Agent Hub/Claw 主 Agent 运行时执行本 Skill。运行时需提供弹窗、文件选择、内置 `atp` 工具调用能力和定时任务能力。

## 本地与运行时边界

- 本地执行：Excel 分析与清洗、清洗文件解析、结果 xlsx 落盘与风险统计。
- 运行时调用：线上价格查询由运行时内置的 `atp` 核价工具（健康中心核价）同步完成。
- “本地”仅描述脚本执行位置；核价调用需运行时联网，不表示离线运行。
- sellerId、商家登录态与会话上下文由运行时在调用 `atp` 时自动注入，脚本不自行签发或缓存任何鉴权凭证。

## 统一 Python 运行时

macOS 和 Windows 统一执行 `scripts/price_check.py`，禁止选择或拼接平台专用脚本。运行时必须通过 PATH 提供 `python` 命令，且版本不低于 3.11；首次执行时用以下命令确认：

```text
python --version
```

`scripts/price_check.py` 只使用 Python 3.11 标准库，覆盖 analyze、clean、batch-check 和 report。批量核价通过 `subprocess` 调用运行时提供的 `atp` 命令；除 `atp` 外，本地流程不依赖第三方包、平台业务脚本或其他外部命令。禁止执行 pip 安装。

## atp 工具依赖

`batch-check` 通过运行时 PATH 上的 `atp` 命令调用核价工具：

```text
atp invoke --code tool_78717bjpsy --version 0.0.2 --params '{"param0":{...}}'
```

- `atp` 命令不存在或不可执行时，属于运行时未就绪，按失败关闭处理：展示原始错误，提示用户升级或重启 Agent Hub，由用户重新发起核价。
- 单批调用的鉴权（商家登录态、sellerId）由 `atp` 与运行时负责，脚本不读取、不缓存、不签发 consumerKey 或任何 token。
- `atp` 返回非零或 `success=false` 由 `batch-check` 按单批 `cli_error` / `biz_fail` 记录并进入限流、熔断逻辑，不在此处单独重试。

## Skill 资源完整性与失败关闭

Skill 目录中的说明、参考文档、脚本和资源文件均视为随安装包发布的只读内容。只允许读取说明和执行脚本；禁止修改、覆盖、删除或在 Skill 目录内创建诊断、修复、备份及过程文件。

以下错误表示本地 Skill 包损坏、脚本编码异常或运行环境不支持，属于不可自动重试错误：

- `python` 命令不存在、版本低于 3.11，或内置运行时尚未就绪。
- 运行时未提供 `atp` 命令，或 `atp` 无法执行。
- 统一 CLI 返回 `SyntaxError`、`Traceback`、`ImportError` 或其他未结构化异常。
- 脚本内容、stdout 或 stderr 出现明显乱码并无法按 UTF-8 解析。
- 脚本输出缺少约定的结构化 JSON 事件（parsed / batch / done），且错误不属于明确的传输类故障。

命中任一情况时：

1. 保留并展示首次执行的原始错误，不改写或掩盖错误信息。
2. 立即结束当前执行，不再次运行同一阶段，也不尝试修改 code page、转码、补写 BOM、字符替换或重建脚本。
3. 禁止安装依赖，或另写程序诊断、修复或替代 Skill 自带脚本。
4. Python 运行时或 `atp` 缺失时提示用户升级或重启 Agent Hub；Skill 文件异常时提示用户从 Skill 市场升级或重新安装。处理完成后，由用户重新发起一次新的核价。
