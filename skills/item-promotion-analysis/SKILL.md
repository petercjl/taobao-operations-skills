---
name: item-promotion-analysis
description: 分析指定商品的付费推广覆盖、流量、花费与成交效率，并与商品自然经营结果对账。适用于推广效果、ROI、渠道结构和预算调整前的诊断。
---

# 商品付费推广分析

## 依赖与输入

- `@petercjl/sycmcli >= 0.4.0`，能力 `business.registered_data.read`、`sycm.item.detail.read`。
- 必填：`store`、一个或多个 `itemId`、`dateRange`；可选目标 ROI、毛利率和推广渠道。
- 当前稳定数据源包括 `item.dmp-product`、`item.dmp-product-top`、`item.flow-source-tree` 与商品概览。若底层没有返回花费字段，不能自行推算 ROI。

## 主线

1. 校验店铺、商品归属和统一周期。
2. 读取商品推广状态/指标、付费渠道流量及商品经营概览；多商品时使用注册的批量 Top 操作并逐项核对。
3. 按渠道汇总平台返回的展现、点击、花费、支付金额、买家和 ROI；字段缺失保持 `null`。
4. 将付费流量与全商品访客/成交对账，只有口径一致且误差可接受时才计算贡献率。
5. 判断覆盖不足、点击效率、转化效率、成本与成交背离；建议最多 3 条，写明数据依据和观察指标。

## 输出

`store`、`itemIds`、`dateRange`、`promotionStatus`、`channelMetrics[]`、`itemTotals`、`reconciliation`、`diagnosis[]`、`actions[]`、`dataGaps[]`。

## 异常与边界

- 只读，不创建计划、不调预算/出价、不主动设置定时任务。
- 毛利、成本或花费缺失时不判断盈利；区间不转为中点。
- 登录、风控、店铺身份恢复遵循 sycmcli；完成后清理临时经营数据。
- 若所需推广接口未在 sycmcli 注册，返回 `CAPABILITY_UNAVAILABLE`，不得直连任意接口。
