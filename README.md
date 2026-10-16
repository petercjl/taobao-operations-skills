# @petercjl/taobao-operations-skills

一个 npm 包统一分发淘宝运营场景的独立 Agent Skills。每个 Skill 保留自己的名称、版本、资源、业务方法、输入输出契约和测试边界；npm 包只负责清单、发现、安装、更新与兼容性状态。

## 责任边界

- 本包中的应用 Skill：负责业务目标、分析方法、工作流、内容选择、项目状态与业务验收。
- `@petercjl/sycmcli`：负责店铺鉴权、专用浏览器、取数、受控填写/提交、回读与恢复。
- Agent 目录：是受管理的安装目标，不是独立源码。

## 当前状态

26 个 Skill 均已进入 canonical source，并保留独立名称、版本和契约。其中 11 个已完成本地真实回归，另外 15 个已完成主流程、能力契约、Codex/SealSeek 适配与静态门禁，状态为 `implemented-awaiting-validation`，等待按 Skill 逐项做真实店铺回归。应用 Skill 不再依赖生意管家专有 `sycm-agent` 或 `eval-merchant-script`；平台取数统一通过 `sycmcli` 的注册能力执行。

`doctor --json` 会分别返回 `implementationGaps` 与 `validationPending`：前者表示尚未实现，后者表示已经实现但仍缺真实环境证据。只有逐项回归通过后，Skill 才会标记为 `implemented-local-validation`。

营销知识 Skill 的规范名称是 `mkt-insight-marketing-knowledge`；旧名称 `mkt_insight-marketing-knowledge` 作为兼容别名继续支持。

## 管理接口

```text
taobao-operations-skills version
taobao-operations-skills capabilities --json
taobao-operations-skills doctor --json
taobao-operations-skills skill list --json
taobao-operations-skills skill source --name <skill> --json
taobao-operations-skills skill status --name <skill> --agent codex --json
taobao-operations-skills skill install --name <skill> --agent codex --json
taobao-operations-skills skill update --name <skill> --agent codex --json
```

安装器默认拒绝覆盖未受管理的同名 Skill。显式采用 `--adopt` 时会先生成可恢复备份；受管理副本出现本地修改时，更新会停止并要求显式 `--reconcile`。macOS 默认使用链接，Windows 使用受管理副本。

## 自动更新

CLI 默认每 24 小时检查一次 `latest`。只有存在稳定新版本时才更新 npm 包，并同步没有本地修改的受管理 Skill。离线或注册表不可用不会中断普通 Skill 管理命令；错误会保存在更新状态中。可通过 `update config` 调整检查间隔或关闭自动更新。
