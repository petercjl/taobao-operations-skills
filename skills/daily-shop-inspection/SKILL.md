---
name: daily-shop-inspection
description: 对指定淘宝或天猫店铺执行每日经营巡检，综合核心指标、商品组合、异常商品与竞对监控信号，输出风险清单和当天优先动作。
---

# 店铺每日巡检

本 Skill 是只读编排入口，面向“今天先看什么”。它不替代单项深度分析，也不生成无数据依据的营销资损结论。

## 依赖

- `shop-core-index-analysis`
- `shop-core-potential-item-analysis`
- 可选 `item-traffic-fluctuation-analysis`、`competitor-comparison-action-tracking`
- `@petercjl/sycmcli >= 0.4.0`：`sycm.shop.performance.read`、`sycm.shop.items.read`、`business.registered_data.read`

运行时按精确名称加载必需 Skill。可选依赖缺失时交付部分巡检并记录缺口。

## 输入

`store` 必填；默认检查最近一个完整自然日，并使用前一同口径周期作比较。可选核心商品数、已监控竞对、关注风险。

## 主线

1. 唯一解析店铺并校验登录身份。
2. 执行店铺核心指标分析，识别销售、访客、买家、转化与退款的显著变化。
3. 执行核心/潜力/引流商品组合分析，识别核心款下滑、流量高转化低、异常增长和退款风险。
4. 读取已注册的巡检/竞争监控操作；只把真实返回的告警纳入清单。
5. 对最重要的商品异常可调用流量波动 Skill 下钻；最多下钻 3 个，避免巡检失控。
6. 按“紧急且影响大—需确认—持续观察”分级，输出当天最多 5 条动作与观察指标。

## 输出

`store`、`inspectionDate`、`comparisonPeriod`、`shopSignals[]`、`itemSignals[]`、`competitionSignals[]`、`risks[]`、`priorities[]`、`recommendedSkills[]`、`dataGaps[]`。

## 异常与边界

- 空数据时说明未取得数据，不等同于“没有问题”。
- 只读，不回复评价、改库存、改投放或新建定时任务。
- 不自动调用不存在的营销风险 Skill；需要额外领域巡检时只建议明确可用的 Skill。
- 完成后清理临时经营数据。

## 验收

每条风险有指标、对象、周期与阈值证据；同一问题不在店铺和商品层重复计数；优先级与证据强度一致。
