---
name: weekly-or-monthly-store-performance-reports
description: 为指定淘宝或天猫店铺生成经营周报、月报和周期复盘。适用于“上周经营怎么样”“生成店铺周报”“本月经营总结”“月会复盘”等请求；读取真实销售、流量和转化数据，输出可追溯的变化判断与行动建议。
---

# 店铺经营周报和月报

本 Skill 负责周期定义、经营解读、报告结构与行动建议。真实取数、店铺身份校验、登录恢复和多店铺浏览器由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.shop.performance.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若未提供目录，执行 `sycmcli skill source --json` 获取 canonical source。完整读取其当前 `SKILL.md` 后执行。
- 兼容判断：检查 sycmcli 版本不低于 `0.4.0`，并确认 `sycmcli capabilities --json` 声明 `sycm.shop.performance.read`。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`；不重建接口，不使用临时抓取脚本。

## 输入

- `store`：店铺别名或显示名称。用户点名时必须匹配；未点名且只有一家可用店铺时可直接使用。
- `period`：`本周`、`上周`、`最近7天`、`本月`、`上月`、`最近30天`，也可使用明确的起止日期。
- `focus`：可选，用户特别关注的指标或经营问题。
- `format`：默认在对话中输出 Markdown；用户要求文件时再保存报告。

用户只说“周报”时默认最近 7 天，只说“月报”时默认最近 30 天，并在标题中展示真实日期范围。

## 周期口径

以店铺所在时区和平台可用数据截止日为准：

- 最近 7 天：`--date-type recent7`
- 最近 30 天：`--date-type recent30`
- 上周：上一自然周周一至周日，使用 `recent7` 并传入明确 `--date-range`
- 本周：本周一至平台可用截止日；若尚无完整一天，说明实际截止日
- 上月：上一自然月首日至末日，使用 `recent30` 并传入明确 `--date-range`
- 本月：本月首日至平台可用截止日
- 明确日期：按用户日期传入 `--date-range START|END`；周期超过接口可接受范围时返回能力缺口，不拆分后伪装成平台环比

报告中的变化率使用平台随本次周期返回的 `comparisons`，不把自行拼接的不同口径数据称作平台环比。

## 主线

### 1. 检查依赖与店铺

1. 加载当前 `sycmcli` Skill，运行 `sycmcli version --json` 和 `sycmcli capabilities --json`。
2. 运行 `sycmcli stores list`，将用户指定的店铺解析为唯一别名。
3. 所有后续命令显式传入 `--store <alias>`。

### 2. 获取真实数据

创建权限为仅当前用户可读写的临时目录，然后运行：

```bash
sycmcli shop summary --store <alias> --date-type <recent7|recent30> --out <temp>/summary.json
```

自然周、自然月或明确日期范围追加：

```bash
--date-range <START|END>
```

`--out` 文件只包含已规范化的数据主体。读取 `dateRange`、`metrics` 和 `comparisons`，不要期待外层 `ok` 包装。

### 3. 生成确定性报告底稿

在本 Skill 目录运行：

```bash
node scripts/report.mjs --input <temp>/summary.json --period-type <weekly|monthly> --store <alias> --label <报告名称>
```

脚本输出结构化 JSON 与 Markdown 底稿。Agent 可依据用户 `focus` 调整叙述顺序，但不得改写数字、夸大因果或超出已取数据范围。

### 4. 校验并交付

- 使用 sycmcli 实际返回的 `dateRange`。
- 金额保留两位小数；比例和变化率转为百分数。
- `null` 表示平台未返回，不能写成 0。
- 所有判断必须能回指到指标或平台变化率。
- 行动建议最多 3 条，每条包含“数据依据 + 建议动作 + 下周期观察指标”。
- 完成后删除临时经营数据；用户要求报告文件时，将最终报告保存到用户指定位置，并在覆盖既有文件前遵守文件保护规则。

## 报告结构

1. 标题、店铺、真实周期与数据截止日
2. 核心指标：销售额、访客数、支付买家数、支付转化率、客单价
3. 周期变化：平台返回的销售、流量、买家、转化和客单变化率
4. 经营判断：流量、转化、客单中哪些因素与销售变化同向或背离
5. 风险与机会：仅陈述本次数据能够支持的内容
6. 下周期行动：最多 3 条，可复核指标明确
7. 数据缺口：平台未返回或当前能力未覆盖的数据

## 输出契约

```json
{
  "store": "店铺别名",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "periodType": "weekly|monthly",
  "metrics": {},
  "comparisons": {},
  "drivers": [],
  "risks": [],
  "actions": [],
  "dataGaps": [],
  "markdown": "# 店铺经营周报..."
}
```

面向用户时直接展示简洁中文报告，不必展示内部 JSON。若用户要求下载，再提供真实可访问的文件路径；不生成虚构下载链接或任务 ID。

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在该店铺的可见 Chrome 中完成登录或验证；用户确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- `CAPABILITY_UNAVAILABLE`：提示更新 `@petercjl/sycmcli`，不使用未注册接口。
- 空数据：返回真实周期和数据缺口，不生成示例数字。
- 部分指标为 `null`：保留其他已返回指标，并在数据缺口中逐项列出。
- 定时报告：只有用户明确要求定时执行时，才使用宿主自动化能力；普通周报或月报不主动创建任务。

## 边界

- 只读，不修改店铺、商品、推广或账户配置。
- 不调用生意管家模型，不依赖专有 `sycm-agent`。
- 当前概览能力不提供渠道、类目、竞店和商品明细；未额外取数时不生成这些结论。
- 不索要 sellerId、cookie 或 token；身份由 sycmcli 与专用店铺浏览器绑定并校验。

## 验收

- 数据来自用户指定且已绑定的店铺。
- 周期、截止日、指标及变化率均可追溯。
- 缺失值未被改写为 0，平台变化率未被冒充为自行计算值。
- 建议与本次证据对应，且不超过 3 条。
- 临时经营数据已清理。
