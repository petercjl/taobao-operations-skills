---
name: dmp-shop-insight
description: 获取达摩盘全店货品洞察中的店铺概览、商品、类目、标签和指标，并分析支付、搜索点击、转化、ROI 与同行同层基准。
---

# 达摩盘全店洞察

## 依赖与授权

- `@petercjl/sycmcli >= 0.4.0`，能力 `business.registered_data.read`。
- 注册操作：`dmp.shop-date-range`、`dmp.shop-overview`、`dmp.shop-items`、`dmp.shop-item-indicators`、`dmp.shop-categories`、`dmp.shop-standard-categories`、`dmp.shop-labels`。
- 授权由所选店铺的 sycmcli 可见 Chrome 持有。DMP 已登录但接口授权缺失时，让用户在该浏览器完成授权；不导出 Cookie/Token。

## 输入

`store`、`endDate`、`period`（默认 30）、可选类目/标签/指标/Top N。首先执行 date-range，确保日期在平台允许范围内。

## 主线

1. 唯一解析店铺并验证绑定身份。
2. 读取可用日期、指标、类目与标签；将用户名称解析为稳定 ID。
3. 读取 overview 和分页 item list，直到达到请求 Top N、无更多页或平台总数；记录完整性。
4. 对齐支付金额、搜索点击、转化、ROI 与同行同层基准。基准字段缺失时不生成差距。
5. 输出商品分层、类目/标签贡献、优劣势指标和最多 3 条运营建议。

## 输出

`store`、`dateRange`、`filters`、`overview`、`items[]`、`categories[]`、`labels[]`、`benchmarkComparisons[]`、`itemSegments[]`、`actions[]`、`completeness`、`dataGaps[]`。

## 异常与边界

- 只运行 sycmcli 注册操作；旧 `scripts/` 仅为迁移参考，不作为正式执行入口。
- 分页未完成时不声称全店覆盖；区间、指数、空值保持原义。
- 只读，不修改 DMP 标签、人群、计划或预算；完成后清理临时经营数据。

## 验收

店铺、日期、筛选条件和分页边界可追溯；同行基准与本店指标口径一致；所有建议有返回字段依据。
