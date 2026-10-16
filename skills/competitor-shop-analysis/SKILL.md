---
name: competitor-shop-analysis
description: 对比本店与一至两个已监控竞店的核心指标、趋势、流量来源、搜索词、客群和头部商品。适用于“竞店对比”“看看某店为什么增长”“对比流量渠道”等请求。
---

# 竞店对比分析

## 依赖与输入

- `@petercjl/sycmcli >= 0.4.0`，能力 `business.registered_data.read`。
- 需要 `store`、一至两个竞店 `sellerId`、`dateRange`；可选关注维度。竞店必须来自用户明确指定或已监控列表，不能仅凭相似名称自动选择。
- 使用注册操作：`competitor.shop-core`、`competitor.shop-trend`、`competitor.shop-flow-source`、`competitor.shop-search-words`、`competitor.shop-crowd`、`competitor.shop-top-items`，可选 `competitor.shop-operation-summary`、`competitor.shop-highlight`、`competitor.shop-strategy`。

## 主线

1. 唯一解析本店与竞店；必要时只读 `competition.shop-monitor-list` 列出候选并让用户确认。
2. 对每个竞店用同一周期取核心指标和趋势；按用户关注点补取渠道、词、客群、商品与运营摘要。
3. 校验每个响应的 sellerId、周期与成功状态；不一致的数据不进入比较。
4. 在同名同口径指标上比较绝对值、平台比较值和趋势方向；区间值保留原样，不取中点。
5. 输出领先项、落后项、差距来源、可能的运营动作证据和最多 3 条追赶建议。没有动作证据时只称“现象”，不推断原因。

## 输出

`store`、`competitors[]`、`dateRange`、`coreComparison[]`、`trendComparison[]`、`trafficComparison[]`、`searchWordComparison[]`、`audienceComparison[]`、`topItemComparison[]`、`operationEvidence[]`、`actions[]`、`dataGaps[]`。

## 异常与边界

- 未监控、权限不足或登录失效时停止，不自动新增监控。
- 可交付部分维度，但必须列出失败操作及受影响结论。
- 只读，不修改竞店列表、商品或投放；完成后清理临时数据。

## 验收

所有比较均同周期同口径；结论可回指到注册操作返回字段；缺失值没有参与排序或差值计算。
