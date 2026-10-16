---
name: item-traffic-analysis
description: 分析指定淘宝或天猫店铺中单个商品的流量来源、渠道贡献、转化效率和平台变化信号。适用于“这个商品流量从哪来”“分析商品流量结构”“哪个渠道贡献最大”“商品流量为什么下降”等请求。
---

# 商品流量来源分析

本 Skill 负责渠道口径、贡献与效率分析、异常判断和行动建议。真实取数、店铺身份校验、登录恢复与多店铺浏览器由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.item.detail.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若未提供目录，执行 `sycmcli skill source --json` 获取 canonical source。完整读取其当前 `SKILL.md` 后执行。
- 兼容判断：检查 sycmcli 版本不低于 `0.4.0`，并确认 `sycmcli capabilities --json` 声明 `sycm.item.detail.read`。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`；不重建接口，不调用旧的远程 Agent。

## 输入

- `store`：店铺别名或显示名称。用户点名时必须唯一匹配。
- `itemId`：商品 ID，必填。未提供时先用已知商品上下文；用户要求“销量最高”时全量读取商品并按 `payItmCnt` 选择，要求“销售额最高”时按 `payAmt` 选择；其他情况请用户提供或经同意先查看排行。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `focus`：可选，例如“自然搜索”“付费流量”“转化差的渠道”。
- `limit`：输出渠道数量，默认 10，范围 1～50。

## 主线

### 1. 检查依赖、店铺与商品

1. 加载当前 `sycmcli` Skill，验证版本和 `sycm.item.detail.read`。
2. 运行 `sycmcli stores list`，将店铺名称解析为唯一别名。
3. 确认 `itemId` 来自用户、当前上下文或同店铺商品排行；不得猜测。排行选择必须执行 `sycmcli shop items --all` 并按用户点名的指标自行排序，不能依赖接口默认顺序。

### 2. 获取真实流量数据

创建权限受限的临时目录，运行：

```bash
sycmcli shop-item flow --store <alias> --item-id <id> --date-type <day|recent7|recent30> --out <temp>/flow.json
sycmcli shop-item overview --store <alias> --item-id <id> --date-type <day|recent7|recent30> --out <temp>/overview.json
```

用户提供明确周期时追加 `--date-range <START|END>`。

`flow.json` 中：

- `tree` 是平台渠道树，适合判断一级来源与下钻关系。
- `channels` 是同一棵树的展平视图，父子渠道可能包含重叠口径，不能直接相加。
- 指标对象保留 `value` 与 `cycleCrc`；比较基期未由平台契约明确时，只称“平台比较值”。

### 3. 生成确定性分析底稿

运行：

```bash
node scripts/analyze.mjs --input <temp>/flow.json --overview <temp>/overview.json --store <alias> --limit <N>
```

脚本只用一级渠道计算渠道树内部结构，避免父子渠道重复计数；同时将渠道树合计与商品概览总量对账。只有两者误差不超过 2% 时才输出全商品贡献率；否则只输出“渠道树内占比”并记录口径缺口。展平渠道仅用于下钻展示。

### 4. 业务解读

按用户关注点优先输出，再给出最小完整判断：

1. 一级渠道结构：访客数、渠道树内访客占比、支付金额、渠道树内成交占比、支付转化率。对账通过时可另列全商品贡献率。
2. 规模渠道：按访客或支付金额识别主力来源。
3. 效率渠道：比较支付转化率，但同时展示样本访客数，避免小样本误导。
4. 变化信号：分别列出同向增长、同向下滑和访客/成交信号背离的渠道，并标明触发指标；比较基期只使用平台原字段语义。
5. 行动建议：最多 3 条，每条写明数据依据、建议动作和下周期观察指标。

若需要理解某个一级渠道的组成，可从 `channels` 中筛选其子级，但不得把父级与子级再次求和。

## 输出契约

```json
{
  "store": "店铺别名",
  "itemId": "商品ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "treeTotals": {},
  "itemTotals": {},
  "reconciliation": {},
  "rootSources": [],
  "topTraffic": [],
  "topSales": [],
  "highConversion": [],
  "growing": [],
  "declining": [],
  "mixed": [],
  "actions": [],
  "dataGaps": []
}
```

面向用户时用简洁中文和小表格展示，不必原样输出 JSON。明确区分平台值、脚本计算占比和业务判断。

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 商品无数据：核对商品是否属于目标店铺及周期内是否有流量；不生成示例数字。
- 渠道树为空：返回真实周期和空数据状态，不将空结果解释为零流量。
- 渠道树合计与商品概览不一致：保留两套总量和相对差异，只将占比称为“渠道树内占比”，不把它解释为全商品贡献率。
- 指标为 `null`：保留缺失语义，不参与排序、占比或阈值计算。
- 定时分析：只有用户明确要求定时执行时，才使用宿主自动化能力；普通分析后不主动创建或推销定时任务。

## 边界

- 只读，不修改商品、投放、出价、预算或账户配置。
- 不调用生意管家模型，不依赖专有 `sycm-agent`。
- 流量来源数据不包含广告成本与利润时，不判断 ROI 或盈利能力。
- 不把渠道相关性描述成确定因果；需要活动、素材或投放动作证据时明确列为数据缺口。
- 完成后删除临时经营数据。

## 验收

- 店铺、商品与周期可追溯。
- 父子渠道没有重复汇总，渠道树与商品概览已对账。
- `null` 未被改写为 0，小样本高转化未被直接称为优质主力渠道。
- 所有结论可回指到渠道指标，建议不超过 3 条。
- 临时经营数据已清理。
