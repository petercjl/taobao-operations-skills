---
name: category-keyword-analysis
description: 分析淘宝或天猫指定叶子类目的搜索关键词排行、搜索访客区间、点击率、支付转化率区间和排行变化。适用于“这个类目有哪些热词”“类目关键词机会”“分析搜索词 Top N”等请求。
---

# 类目关键词分析

本 Skill 负责类目口径、关键词比较方法和业务解读。真实取数、店铺身份校验、登录恢复和关键词排行分页由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.category.read`、`sycm.market.keyword_rank.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若目录未提供，执行 `sycmcli skill source --json` 获取 canonical source。完整读取当前 `SKILL.md` 后执行。
- 兼容判断：确认版本不低于 `0.4.0`，并检查 `sycmcli capabilities --json` 声明两项必需能力。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`。

## 输入

- `store`：用于访问生意参谋市场数据的已授权店铺别名或显示名称。
- `categoryId`：叶子类目 ID；与 `categoryName` 至少提供一项。
- `categoryName`：类目名称或关键词，用于定向解析叶子类目。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `rankType`：关键词排行类型，默认 `hot`。
- `top`：分析数量，默认 50，范围 1～200。

## 主线

### 1. 校验依赖与店铺

1. 加载当前 `sycmcli` Skill，验证版本和两项能力。
2. 运行 `sycmcli stores list`，将店铺名称解析为唯一别名。

### 2. 解析叶子类目

用户只提供类目名称时运行：

```bash
sycmcli category search --store <alias> --keyword <类目名称>
```

只在结果唯一或用户已明确选择时使用叶子类目 ID。多个候选会改变市场口径，应把简短候选交给用户选择。

### 3. 获取关键词排行

创建权限受限的临时目录，运行：

```bash
sycmcli keyword rank \
  --store <alias> \
  --cate-id <leaf-category-id> \
  --rank-type <type> \
  --date-type <type> \
  --top <N> \
  --page-size 20 \
  --out <temp>/keyword-rank.json
```

用户提供明确周期时追加 `--date-range <START|END>`。检查 `returnedCount`、`recordCount`、`fetchedPages`、`stoppedBy`、`duplicateCount` 和 `warnings`，不能把不完整结果称为完整 Top N。

### 4. 生成确定性分析底稿

```bash
node scripts/analyze.mjs --input <temp>/keyword-rank.json --store <alias> --limit <N>
```

脚本保留平台返回的排行和指标，输出：

- Top 关键词及排行变化；
- 搜索访客区间分布；
- 支付转化率区间分布；
- 有明确环比时的上升、下降与持平数量；
- 最多 3 条基于真实排行的后续研究建议。

平台返回区间时必须保留区间，不得取中点伪装成精确值。`clickThroughRate` 只作为平台返回值展示，不自行补百分号或改单位。

### 5. 业务解读

1. 说明店铺、类目、周期、排行类型和 Top N 完整性。
2. 用小表格展示关键词、排名、搜索访客区间、点击率返回值、支付转化率区间与环比。
3. 说明头部关键词覆盖的搜索意图，可把词语用于标题研究、竞品搜索和人群假设，但不把词频或排名解释为成交原因。
4. 输出最多 3 条下一步建议，并标注证据来自哪一行排行或哪个区间分组。

## 输出契约

```json
{
  "store": "店铺别名",
  "categoryId": "叶子类目ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "rankType": "hot",
  "completeness": {},
  "topKeywords": [],
  "trafficBandDistribution": [],
  "payRateBandDistribution": [],
  "movementSummary": {},
  "actions": [],
  "dataGaps": []
}
```

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 类目候选不唯一：请用户选择叶子类目，不跨类目拼接关键词排行。
- 市场权限不足或排行为空：如实返回权限或空数据状态，不生成示例关键词。
- 指标为 `null`：保留缺失语义，不参与比较或排序。

## 边界

- 只读，不修改标题、商品、广告或店铺配置。
- 排名、搜索访客区间、点击率返回值和支付转化率区间是不同指标，不合成为虚构的机会分。
- 不把关键词排行解释为精确搜索量、精确成交量、竞争度、市场份额或因果关系。
- 完成后删除临时经营数据。

## 验收

- 店铺、叶子类目、周期、排行类型可追溯。
- 分页与 Top N 完整性明确，重复关键词已处理。
- 平台区间与缺失值原样保留，计算口径无伪精确。
- 建议有排行或区间证据，且不超过 3 条。
- 临时经营数据已清理。
