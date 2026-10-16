---
name: item-traffic-fluctuation-analysis
description: 定位指定商品流量上涨或下跌来自哪些日期和渠道，并区分流量规模、转化与成交信号。适用于“这个商品最近流量为什么波动”“哪个渠道掉了”等请求。
---

# 商品流量波动分析

## 依赖与输入

- 精确依赖 `item-traffic-analysis`。
- `@petercjl/sycmcli >= 0.4.0`，能力 `sycm.item.detail.read` 与注册数据读。
- 输入：`store`、`itemId`、观察期、等长对比期或平台比较口径、可选阈值。默认显著变化阈值 20%，但必须同时满足最小样本量。

## 主线

1. 校验商品、观察期和对比期；店铺和 itemId 必须一致。
2. 分别执行 `item-traffic-analysis` 获取两个周期的一级渠道结构，并用 `item.detail`/趋势注册操作取得逐日变化。
3. 按渠道稳定 ID 或精确名称对齐，计算访客、支付金额、买家和转化变化；父子渠道不重复相加。
4. 把异动分为规模同向、效率同向、流量成交背离、新增渠道、消失渠道；小样本只列观察，不列核心原因。
5. 将日趋势峰谷与渠道贡献交叉验证，输出最多 3 个核心来源及下一步检查动作。

两期渠道对齐与异动分类使用 `scripts/analyze.mjs` 的 `analyzeTrafficFluctuation()`，输入为两期 `item-traffic-analysis` 结构化结果。

## 输出

`itemId`、`currentWindow`、`comparisonWindow`、`overallChange`、`dailyAnomalies[]`、`channelChanges[]`、`drivers[]`、`mixedSignals[]`、`actions[]`、`dataGaps[]`。

## 边界与验收

- 不把平台比较值误称为指定对比期；无法确认基期时显式说明。
- `null`、区间和小样本保持原语义，不制造精确原因。
- 只读，不调整渠道或投放；完成后清理临时数据。
