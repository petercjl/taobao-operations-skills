---
name: category-market-insight
description: 编排淘宝或天猫品类市场洞察，从类目解析、榜单、关键词、价格带到竞争格局，交付一份可追溯的综合洞察。适用于“完整分析这个品类”“品类竞争格局与机会”等请求。
---

# 品类市场洞察

本 Skill 只拥有业务编排与综合判断，不重复实现取数。它在一个 npm 包内精确加载独立 Skill，并把每一步的真实输出传给下一步。

## 依赖

- `category-best-selling-items-analysis`
- `category-keyword-analysis`
- `category-price-band-analysis`
- `category-top-items-profile`
- `category-top-shops-profile`
- `category-market-analysis`
- `@petercjl/sycmcli >= 0.4.0`：`sycm.category.read`、`sycm.market.item_rank.read`、`sycm.market.keyword_rank.read`、`sycm.market.price_segments.read`

按精确名称从宿主目录加载每个依赖的完整 `SKILL.md`。缺失时返回 `DEPENDENCY_MISSING`；不得模仿或重建缺失 Skill。

## 输入

`store`、`category` 或 `cateId`、`dateType`、`dateRange`、可选 `topN`、`rankType`、`focus`、输出目录。默认近 7 天，默认 Top 100；影响成本或范围时先明确口径。

## 主线

1. 解析唯一店铺与叶子类目，建立同一 `runId`、周期和临时工作目录。
2. 分别执行热销商品、关键词、价格带分析；每一步先验收完整性和身份。
3. 基于热销商品结果执行头部商品与头部店铺画像。
4. 将榜单与价格带证据交给 `category-market-analysis` 计算集中度、价格结构、卖点/KANO 结论；权威卖点信号不可用时显式降级。
5. 综合为：市场结构、头部竞争、需求词、价格机会、商品与店铺模式、风险、最多 5 条机会建议。建议必须引用一个或多个上游证据。
6. 输出 Markdown 摘要及结构化 JSON；只有用户明确要求时再生成 HTML/Excel。

## 输出

`runId`、`store`、`category`、`dateRange`、`sourceStatus`、`marketStructure`、`itemProfile`、`shopProfile`、`keywordOpportunities`、`priceOpportunities`、`actions`、`artifacts`、`dataGaps`。

## 恢复与边界

- 任一来源失败时可交付 `partial`，但必须列明缺失模块及受影响结论。
- 跨模块的店铺、类目和周期不一致时停止，不拼接。
- 只读，不修改商品、价格、投放或监控配置；临时经营数据完成后清理。

## 验收

- 所有独立 Skill 的返回状态已检查，结论能回指到来源。
- 没有把区间值中点、缺失值或样本份额伪装成精确全市场指标。
- 综合建议与用户关注点一致，且未越过取数证据。
