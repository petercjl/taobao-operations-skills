---
name: category-top-items-profile
description: 归纳淘宝或天猫指定叶子类目 Top 商品的定位特征、平台核心关键词、店铺重复上榜结构和排行变化。适用于“Top 商品有什么共性”“类目爆款画像”“榜单商品结构”等请求。
---

# 类目 Top 商品画像

本 Skill 聚焦“头部商品画像”，不重复实现市场排行取数。它组合 `category-best-selling-items-analysis` 的当前输出，再把排行证据整理为商品定位画像。

## 运行依赖

- 逻辑依赖 Skill：`category-best-selling-items-analysis`，最低契约版本 `3.0.0`
- 间接能力包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 解析方式：从宿主广告的 Skill catalog 或当前套件执行 `taobao-operations-skills skill source category-best-selling-items-analysis --json`，按精确名称加载并完整读取其 `SKILL.md`。
- 必需上游输出：`store`、`categoryId`、`dateRange`、`rankType`、`completeness`、`topItems`、`keywordFrequency`、`shopDistribution`、`dataGaps`。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CONTRACT_MISMATCH`，不自行复制或重建上游取数流程。
- 返回主线：上游完成后，把其结构化结果交给本 Skill 的确定性脚本，然后继续画像解读。

## 输入

- `store`、`categoryId` 或 `categoryName`、`dateType`、`dateRange`、`rankType`、`top`：原样传给上游 Skill。
- `profileLimit`：画像中保留的头部商品数，默认 20，范围 1～100。

## 主线

### 1. 执行上游排行分析

加载并执行 `category-best-selling-items-analysis`。上游负责店铺解析、叶子类目确认、真实排行分页、隐私字段省略和临时原始数据清理。

如果上游 `completeness.completeForRequestedTop` 不为 `true`，本 Skill 可以输出部分画像，但必须标记 `partial`，不能称为完整 Top N 画像。

### 2. 生成确定性画像底稿

把上游结构化 JSON 保存到权限受限的临时文件，运行：

```bash
node scripts/analyze.mjs \
  --input <temp>/best-selling-analysis.json \
  --limit <profileLimit>
```

脚本输出：

- 头部商品清单及平台返回指标；
- 平台核心关键词覆盖率；
- 重复上榜店铺及席位数；
- 有明确排行比较值时的上升、下降、持平与缺失数量；
- 最多 3 条画像研究建议。

### 3. 画像解读

1. 说明店铺、类目、周期、排行类型、样本数量和完整性。
2. 用平台 `coreKeywords` 概括头部商品定位，不从标题强行切词或推断材质、功能、价格与人群。
3. 店铺席位数只描述本次榜单样本，不等于店铺市场份额。
4. 排名比较值只在上游明确返回时解释；缺失时不判断趋势。
5. 输出最多 3 条可用于竞品选样、标题研究或商品定位验证的下一步建议。

## 输出契约

```json
{
  "status": "success|partial",
  "store": "店铺别名",
  "categoryId": "叶子类目ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "rankType": "gmv",
  "sample": {},
  "topItems": [],
  "positioningKeywords": [],
  "recurringShops": [],
  "rankMovementSummary": {},
  "actions": [],
  "dataGaps": []
}
```

## 异常与恢复

- 上游认证、类目歧义、权限和空数据错误：保留上游错误码与恢复方式。
- 上游输出缺字段：返回 `CONTRACT_MISMATCH`，不猜测字段。
- 指标或排名比较值为 `null`：保留缺失语义。
- 本地底稿脚本失败：停止并返回 `CATEGORY_TOP_ITEMS_PROFILE_FAILED`。

## 边界

- 只读，不修改商品、标题、价格、广告或店铺配置。
- 平台关键词覆盖、榜单席位和排行变化是描述性证据，不证明购买原因、市场份额或利润。
- 不把标题词频当作平台核心关键词；不使用未返回的评价、属性、售价或销量字段。
- 完成后删除临时分析文件。

## 验收

- 精确加载并执行上游 Skill，依赖闭包可追溯。
- 画像样本与上游 Top 商品逐行一致。
- 关键词只来自平台 `coreKeywords`，排行变化保留缺失值。
- 输出完整性和局限明确，建议不超过 3 条。
- 临时文件已清理。
