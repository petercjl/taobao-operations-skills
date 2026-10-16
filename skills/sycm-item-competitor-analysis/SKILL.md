---
name: sycm-item-competitor-analysis
description: 对比本店商品与明确竞品的核心指标、趋势、流量来源和入店搜索词。适用于商品竞品对比、支付转化率对比、渠道差距和搜索词差距分析。
---

# 商品竞品对比

## 依赖与输入

- `@petercjl/sycmcli >= 0.4.0`，能力 `business.registered_data.read`。
- 必填：`store`、`selfItemId`、`dateType`、`dateRange`；对比阶段还需用户确认的 `rivalItemId`。
- 注册操作：`competitor.search`、`competitor.recommend`、`competitor.core-indexes`、`competitor.core-trend`、`competitor.flow-origin`、`competitor.flow-source`、`competitor.flow-paid`、`competitor.search-words`。

## 主线

1. 校验店铺身份、商品 ID 和周期。缺少竞品时运行 search/recommend 只返回候选，由用户确认后继续。
2. 用 `sycmcli data run --operation competitor.core-indexes` 取得核心指标。
3. 按诉求补取趋势、流量来源、付费来源和搜索词；所有操作传同一 itemId、rivalItemId、dateRange。
4. 校验响应状态、对象和周期，将本品/竞品按同名指标与渠道对齐。
5. 输出规模、效率、趋势、渠道和词的差距；竞品脱敏区间保持原值，不用中点计算差额。
6. 最多给 3 条建议，每条引用具体差距与下周期观察指标。

## 输出

`selfItemId`、`rivalItemId`、`dateRange`、`coreMetrics`、`trends`、`trafficSources`、`paidSources`、`searchWords`、`gaps[]`、`actions[]`、`dataGaps[]`。

## 异常与边界

- 登录或风控交给 sycmcli 管理浏览器，用户完成后重试一次。
- 竞品未确认、权限不足或身份不符时停止。
- 只读，不自动添加监控、改价或建推广；旧 `scripts/` 仅作为接口研究资料，正式执行统一走 sycmcli 注册操作。
- 完成后清理临时经营数据。
