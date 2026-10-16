---
name: market-blue-ocean-opportunity-mining
description: 从类目商品榜、关键词榜与价格带数据中筛选供需错配的蓝海候选，并给出验证优先级。适用于“找蓝海类目/关键词/价格带”“发现商品开发机会”等请求。
---

# 市场蓝海机会发现

本 Skill 发现“值得验证的候选”，不把榜单样本直接称为确定蓝海。

## 依赖与输入

- `category-keyword-analysis`、`category-price-band-analysis`、`category-best-selling-items-analysis`。
- `@petercjl/sycmcli >= 0.4.0` 对应市场读能力。
- 输入：`store`、一个或多个叶子类目、统一 `dateRange`、候选上限、可选成本/毛利/供应约束。

## 主线

1. 对每个类目加载三个依赖 Skill 的当前契约，取得完整性经过验证的关键词、价格带和头部商品结果。
2. 构造可解释信号：搜索规模/变化、点击和支付效率、商品与店铺集中度、价格带拥挤度、头部标题卖点重复度。
3. 所有信号在同一批候选内做分位归一；缺失信号不计 0，而是降低证据覆盖率。
4. 生成候选分数：需求 35%、效率 25%、竞争缺口 25%、增长 15%。用户有毛利或供应约束时只作门槛，不由本 Skill猜测成本。
5. 输出高、中、观察三档；每个候选给出证据、反证、最小验证动作和停止条件。

候选归一、覆盖率和分数使用 `scripts/analyze.mjs` 的 `mineOpportunities()`，不得由模型重新手算排名。

## 输出

`dateRange`、`scope`、`methodology`、`candidates[]`（类目/词/价格带、各信号、score、evidenceCoverage、confidence）、`validationPlan[]`、`dataGaps[]`。

## 边界与验收

- 不把相关性写成因果，不预测确定销量或利润。
- 类目间口径、周期或榜单深度不一致时不得直接比较。
- 区间指标保留区间；不足 3 个有效信号的候选不能进入高优先级。
- 只读，不自动选品、发布、改价或建推广计划；临时数据完成后清理。
