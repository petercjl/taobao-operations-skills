---
name: shop-core-index-analysis
description: 分析指定淘宝/天猫店铺在一天、最近7天、最近30天或明确日期范围内的销售、流量和转化表现。适用于“店铺最近经营怎么样”“查看核心数据”“分析销售额、访客、转化率及变化”等请求。
---

# 店铺核心指标分析

本 Skill 负责业务口径、指标解读、异常判断和行动建议。真实取数、店铺身份校验、登录恢复与多店铺浏览器由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`，由 Codex 或 SealSeek 的适配器保证，不要求 sycmcli 运行时重复声明。
- sycmcli 必需能力：`sycm.shop.performance.read`
- 解析方式：从宿主公开的 Skill 目录按精确名称查找 `sycmcli`；若目录未提供，则执行 `sycmcli skill source --json` 获取其 canonical source。完整读取该 Skill 的当前 `SKILL.md`，再按其多店铺、认证和安全约束执行。
- 兼容判断：先检查 sycmcli 版本不低于 `0.4.0`，再检查 `sycmcli capabilities --json` 是否声明 `sycm.shop.performance.read`。`command.execute` 在本 Skill 的平台适配器中校验。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，说明需要安装或更新 `@petercjl/sycmcli`；不重建接口、不改用临时脚本。
- 返回主线：完成真实取数后回到本 Skill 的“分析与交付”。

## 输入

- `store`：店铺别名。用户点名店铺时必传；未点名时可使用 sycmcli 当前店铺。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`；提供后优先于自动周期。
- `focus`：可选，用户特别关注的指标或问题。
- `trendIndex`：可选，需要趋势时指定单个指标，例如 `payAmt`、`uv` 或 `payRate`。
- `categoryId`：可选趋势类目。未提供时从当前店铺同周期的交易类目列表中选择首项，并在结果中说明。

## 主线

### 1. 确认依赖与店铺

1. 加载当前 `sycmcli` Skill，并运行 `sycmcli version` 与 `sycmcli capabilities --json`。
2. 确认版本不低于 `0.4.0` 且存在 `sycm.shop.performance.read`。
3. 运行 `sycmcli stores list`，解析目标店铺。用户明确指定店铺时，必须匹配其别名或显示名称；存在歧义时再请用户选择。
4. 后续所有命令都显式传入 `--store <alias>`。

### 2. 获取真实数据

运行：

```bash
sycmcli shop summary --store <alias> --date-type <day|recent7|recent30>
```

用户提供 `dateRange` 时追加 `--date-range <START|END>`。

用户需要趋势时，先运行：

```bash
sycmcli shop categories --store <alias> --date-type <day|recent7|recent30>
```

用户提供 `categoryId` 时必须确认它在返回列表中；未提供时选择列表首项，并保留其 `categoryName` 作为选择依据。随后运行：

```bash
sycmcli shop trend --store <alias> --category-id <id> --index-code <metric> --date-type <recent7|recent30>
```

每次趋势调用只查询一个指标。类目列表为空时保留概览分析，并明确说明趋势尚未采集；不得用市场排行类目 ID 代替。

趋势解读优先使用 CLI 返回的 `points` 日期和值。`points` 为空时只描述数值序列，不自行推导逐点日期。

### 3. 校验数据

- `ok` 必须为 `true`。
- 返回的 `store` 必须是目标别名，`identity.stableId` 必须存在并通过 sycmcli 绑定校验。
- 使用返回的 `dateRange` 作为报告周期，不自行改写。
- `null` 表示平台未返回，不能解释为 0。
- 百分比字段按平台的小数比例展示，例如 `0.0967` 显示为 `9.67%`；金额保留两位小数。
- 若登录失效、出现滑块、风控或身份不匹配，停止分析并按 sycmcli 指引让用户在对应可见浏览器完成操作。

## 分析与交付

优先回答用户关心的问题，再给出最小完整经营判断：

1. 核心结果：销售额、访客数、支付买家数、支付转化率、客单价。
2. 变化判断：使用 `comparisons` 中平台返回的变化率，指出增长与下滑最明显的指标。
3. 漏斗判断：结合访客、下单买家、支付买家、下单转化率、支付转化率和下单到支付转化率定位主要损耗环节。
4. 经营结论：区分流量驱动、转化驱动、客单驱动或多因素共同变化。
5. 行动建议：最多 3 条，每条都对应本次数据证据；不扩展到未取数的商品、渠道或人群结论。

客单价优先使用平台返回的 `payPct`。只有该字段缺失且销售额与支付买家数都有效时，才计算 `payAmt / payBuyerCnt`，并标明为计算值。

## 输出结构

```json
{
  "store": "店铺别名",
  "identity": "已校验的店铺身份",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "coreMetrics": {
    "payAmt": null,
    "uv": null,
    "payBuyerCnt": null,
    "payRate": null,
    "payPct": null
  },
  "comparisons": {},
  "trend": null,
  "diagnosis": [],
  "actions": [],
  "dataGaps": []
}
```

面向用户时使用简洁中文，不必原样展示 JSON。明确区分平台返回值、计算值和业务判断。

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在该店铺的可见 Chrome 中完成登录或验证；用户确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- `CAPABILITY_UNAVAILABLE`：提示更新 `@petercjl/sycmcli`，不使用未注册接口。
- 空数据：核对店铺、周期和权限后如实返回数据缺口，不生成示例数字。
- 定时执行：只有用户明确提出定时或周期运行时，才使用宿主提供的自动化能力创建任务；普通分析完成后不主动追加定时询问。

## 验收

- 数据来自已绑定店铺的 sycmcli 结果，没有模拟值。
- 店铺、身份和周期都可追溯。
- 缺失值未被改写为 0。
- 结论可回指到返回指标，建议不超出数据范围。
- 未调用生意管家模型，也未依赖专有 `sycm-agent`。
