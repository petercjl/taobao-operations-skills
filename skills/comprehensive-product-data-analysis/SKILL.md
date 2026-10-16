---
name: comprehensive-product-data-analysis
description: 综合诊断指定淘宝或天猫店铺中的单个商品，联合分析经营概览、平台诊断、详情漏斗和流量来源。适用于“这个商品整体表现怎么样”“做一次单品综合诊断”“这个商品的问题在哪里”等请求。
---

# 单品综合诊断

本 Skill 负责综合诊断方法、证据优先级、问题归纳和行动建议。真实取数、店铺身份校验、登录恢复与多店铺浏览器由 `sycmcli` 提供；渠道结构分析复用独立 Skill `item-traffic-analysis`。

## 运行依赖

### sycmcli

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 必需能力：`sycm.item.detail.read`
- 解析方式：按精确名称从宿主 Skill 目录加载；若宿主未提供目录，执行 `sycmcli skill source --json` 获取 canonical source。完整读取当前 `SKILL.md` 后执行。
- 兼容判断：验证版本不低于 `0.4.0`，并确认 `sycmcli capabilities --json` 声明必需能力。

### item-traffic-analysis

- 逻辑依赖名：`item-traffic-analysis`
- 必需契约：`item.traffic-source.analyze`，Skill 版本不低于 `3.0.0`
- 解析方式：在当前应用 Skill 包或宿主已安装目录中按精确名称加载，完整读取它的 `SKILL.md`，再使用其确定性分析脚本处理本次 `flow.json`。
- 输入交接：同一店铺、商品、周期的 `flow.json` 与 `overview.json`。
- 输出交接：`treeTotals`、`itemTotals`、`reconciliation`、`topTraffic`、`topSales`、`highConversion`、`growing`、`declining`、`mixed`、`actions` 和 `dataGaps`。
- 失败行为：流量分析失败时保留概览、诊断和漏斗结果，将流量标记为数据缺口；完成或失败后都返回本 Skill 主线。

依赖缺失或能力不兼容时返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli` 或当前应用 Skill 包。

## 输入

- `store`：店铺别名或显示名称。用户点名时必须唯一匹配。
- `itemId`：商品 ID。优先从用户或当前商品上下文取得；无法唯一确定时请用户提供，或经用户同意先查看商品排行。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `focus`：可选，用户特别关注的问题。
- `limit`：流量渠道展示数量，默认 10，范围 1～50。

## 主线

### 1. 校验依赖、店铺和商品

1. 加载并校验两个依赖的版本与能力契约。
2. 运行 `sycmcli stores list`，将店铺名称解析为唯一别名。
3. 确认商品 ID 属于目标店铺上下文；不得猜测商品 ID。

### 2. 获取四组同周期数据

创建权限受限的临时目录，依次执行：

```bash
sycmcli shop-item overview --store <alias> --item-id <id> --date-type <type> --out <temp>/overview.json
sycmcli shop-item diagnose --store <alias> --item-id <id> --date-type <type> --out <temp>/diagnose.json
sycmcli shop-item detail --store <alias> --item-id <id> --date-type <type> --out <temp>/detail.json
sycmcli shop-item flow --store <alias> --item-id <id> --date-type <type> --out <temp>/flow.json
```

用户提供明确周期时，每条命令追加 `--date-range <START|END>`。四个结果的 `itemId`、`dateType` 与 `dateRange` 必须一致。

### 3. 分析流量来源

按 `item-traffic-analysis` 的当前说明运行其确定性脚本：

```bash
node <item-traffic-analysis>/scripts/analyze.mjs \
  --input <temp>/flow.json \
  --overview <temp>/overview.json \
  --store <alias> \
  --limit <N> > <temp>/traffic-analysis.json
```

渠道贡献只汇总一级来源，并按该 Skill 的规则完成渠道树与商品概览对账。

### 4. 生成综合诊断底稿

运行：

```bash
node scripts/analyze.mjs \
  --overview <temp>/overview.json \
  --diagnose <temp>/diagnose.json \
  --detail <temp>/detail.json \
  --traffic <temp>/traffic-analysis.json \
  --store <alias>
```

脚本保留平台指标值、平台比较值和缺失值，提取核心经营指标、平台诊断字段、详情漏斗、主要渠道、优势、风险和最多 3 条证据化动作。

### 5. 业务解读

按以下顺序输出：

1. 商品概况：销售额、访客、支付买家、支付转化率、访客价值和退款金额。
2. 变化与平台诊断：分别标注平台周期比较值和平台诊断比较字段；契约未说明比较基期或口径时不改称环比、同比或行业均值。
3. 详情漏斗：展示曝光、互动、收藏、加购、下单、支付与主要流失阶段。
4. 流量结构：展示主要访客来源、成交来源、高效渠道与下滑或信号背离渠道；对账不一致时只称渠道树内占比。
5. 综合结论：最多 3 个优先问题或优势。
6. 行动建议：最多 3 条，每条写明数据依据、动作和下周期观察指标。

若用户指定 `focus`，优先回答该问题，再给出最小完整综合诊断。

## 输出契约

```json
{
  "store": "店铺别名",
  "itemId": "商品ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "coreMetrics": {},
  "platformDiagnosis": {},
  "funnelStages": [],
  "traffic": {},
  "strengths": [],
  "risks": [],
  "actions": [],
  "dataGaps": []
}
```

面向用户时使用简洁中文和小表格，不必原样输出 JSON。明确区分平台原值、脚本计算值和业务判断。

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 某一模块为空：保留其余真实模块并列入 `dataGaps`；核心概览为空时不生成综合结论。
- 指标为 `null`：保留缺失语义，不参与排序、阈值或计算。
- 平台比较字段语义不完整：只称“平台比较值”或“平台诊断字段”。
- 定时分析：只有用户明确要求时才使用宿主自动化能力。

## 边界

- 只读，不修改商品、价格、库存、投放、预算或店铺设置。
- 退款金额不能替代退款原因；流量变化不能单独证明素材、活动或投放导致。
- 没有成本、毛利和广告花费时，不判断利润或 ROI。
- 完成后删除临时经营数据。

## 验收

- 店铺、商品、周期一致且可追溯。
- 四组数据都来自已绑定店铺；缺失模块已明确说明。
- 父子渠道未重复汇总，渠道树已与商品概览对账，`null` 未被改写为 0。
- 综合结论能回指到指标或模块，建议不超过 3 条。
- 临时经营数据已清理。
