---
name: category-best-selling-items-analysis
description: 分析淘宝或天猫指定叶子类目的热销商品排行、头部商品指标、核心关键词和店铺分布。适用于“这个类目卖得最好的商品”“类目热销 Top 商品有什么特征”“分析类目爆款”等请求。
---

# 类目热销商品分析

本 Skill 负责类目口径、排行方法、特征归纳和业务解读。真实取数、店铺身份校验、登录恢复与市场排行分页由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.category.read`、`sycm.market.item_rank.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若目录未提供，执行 `sycmcli skill source --json` 获取 canonical source。完整读取当前 `SKILL.md` 后执行。
- 兼容判断：确认版本不低于 `0.4.0`，并检查 `sycmcli capabilities --json` 声明两项必需能力。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`。

## 输入

- `store`：用于访问生意参谋市场数据的已授权店铺别名或显示名称。
- `categoryId`：叶子类目 ID；与 `categoryName` 至少提供一项。
- `categoryName`：类目名称或关键词，用于定向解析叶子类目。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `rankType`：`gmv`、`growth`、`flow`、`add` 或 `newitm_ipv`，默认 `gmv`。
- `top`：分析数量，默认 20，范围 1～200。

## 主线

### 1. 校验依赖与店铺

1. 加载当前 `sycmcli` Skill，验证版本和两项能力。
2. 运行 `sycmcli stores list`，将店铺名称解析为唯一别名。

### 2. 解析叶子类目

用户只提供类目名称时运行：

```bash
sycmcli category search --store <alias> --keyword <类目名称>
```

只在结果唯一或用户已明确选择时使用叶子类目 ID。多个相近叶子类目会导致市场口径不同，应把简短候选交给用户选择，不能自动合并或猜测。

### 3. 获取排行

创建权限受限的临时目录，运行：

```bash
sycmcli item rank \
  --store <alias> \
  --cate-id <leaf-category-id> \
  --rank-type <type> \
  --date-type <type> \
  --top <N> \
  --out <temp>/item-rank.json
```

用户提供明确周期时追加 `--date-range <START|END>`。检查 `returnedCount`、`recordCount`、`fetchedPages`、`stoppedBy`、`duplicateCount` 和 `warnings`，不能把不完整结果称为完整 Top N。

### 4. 生成确定性分析底稿

运行：

```bash
node scripts/analyze.mjs --input <temp>/item-rank.json --store <alias> --limit <N>
```

脚本保留排行和平台返回指标，提取：

- Top 商品及排名变化；
- 支付买家、访客、搜索访客、加购和收藏等可用指标；
- 平台返回核心关键词的出现频次；
- 头部店铺分布；
- 有足够访客时的“支付买家/访客”计算比值。

该计算比值不是平台支付转化率，必须明确标注为脚本计算值。

### 5. 业务解读

1. 说明类目、周期、排行类型、Top N 完整性。
2. 用小表格展示头部商品的排名、标题、店铺和实际返回指标。
3. 汇总核心关键词及覆盖商品数，只把平台返回的 `coreKeywords` 当作关键词证据。
4. 说明头部店铺集中度；商品行可能来自同一店铺，不能把商品数当作市场份额。
5. 输出最多 3 条可用于选品、标题研究或竞品下钻的下一步建议，并写明数据依据。

## 输出契约

```json
{
  "store": "店铺别名",
  "categoryId": "叶子类目ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "rankType": "gmv",
  "completeness": {},
  "topItems": [],
  "keywordFrequency": [],
  "shopDistribution": [],
  "actions": [],
  "dataGaps": []
}
```

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 类目候选不唯一：请用户选择叶子类目，不跨类目拼接排行。
- 市场权限不足或排行为空：如实返回权限或空数据状态，不生成示例商品。
- 指标为 `null`：保留缺失语义，不参与比值或排序。

## 边界

- 只读，不关注竞品、不修改商品或店铺配置。
- 排名不等于具体销售额；接口未返回销售额、价格、成本、利润或市场份额时不得补算。
- 标题关键词共现不证明购买原因，也不代表商标或品类属性。
- 完成后删除临时经营数据。

## 验收

- 店铺、叶子类目、周期、排行类型可追溯。
- 分页与 Top N 完整性明确，重复商品已处理。
- 内部卖家或用户身份编号不出现在结果中。
- 特征结论来自平台指标或核心关键词，计算比值标注清楚。
- 临时经营数据已清理。
