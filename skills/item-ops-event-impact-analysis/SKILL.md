---
name: item-ops-event-impact-analysis
description: 分析一次明确商品运营动作前后的销售、流量、转化和渠道变化，控制周期与趋势干扰后给出影响判断。适用于改标题、换图、调价、活动或投放调整后的复盘。
---

# 商品运营动作影响分析

## 依赖与输入

- `comprehensive-product-data-analysis`，运行时按精确名称加载当前 Skill。
- `@petercjl/sycmcli >= 0.4.0`，能力 `sycm.item.detail.read`、`sycm.item.gallery.read`。
- 输入：`store`、`itemId`、`eventType`、准确 `eventAt`、变更内容、前后窗口长度；可选同期对照商品或排除日期。

## 主线

1. 生成等长且不重叠的前窗和后窗，事件日单列；若数据粒度不支持则停止。
2. 分别执行综合单品分析，确保店铺、商品、指标口径一致。
3. 比较支付金额、访客、买家、转化、退款、主要渠道和素材表现；缺失值不补 0。
4. 若有对照商品，计算差分变化；没有对照时仅称“事件前后变化”，不声称因果。
5. 检查大促、断货、价格、投放、行业波动等混杂因素，并给出置信度。
6. 输出保留/回滚/继续观察建议及下一观察窗口。

指标前后差异和可选对照差分使用 `scripts/analyze.mjs` 的 `analyzeEventImpact()`；业务层只解释脚本结果与混杂因素。

## 输出

`event`、`preWindow`、`postWindow`、`metricChanges[]`、`channelChanges[]`、`controlComparison`、`confounders[]`、`impactAssessment`、`confidence`、`actions[]`、`dataGaps[]`。

## 边界与验收

- 只读，不执行回滚或再次修改商品。
- 前后窗口必须可追溯且长度相等；事件信息不明确时先询问。
- 没有对照与混杂证据时，结论使用相关性语言。
- 临时经营数据完成后清理。
