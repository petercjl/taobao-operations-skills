---
name: sycm-item-rank-helper
description: 生意参谋商品排行与单品数据查询入口。负责把自然语言映射为店铺商品排行、单品概览、趋势、流量、素材等 sycmcli 只读命令，并返回可追溯原始数据；不承担深度业务诊断。
---

# 商品排行与单品取数入口

## 依赖

精确加载 `sycmcli` Skill；要求 `@petercjl/sycmcli >= 0.4.0`，能力 `sycm.shop.items.read`、`sycm.item.detail.read`，素材请求另需 `sycm.item.gallery.read`。

## 输入路由

- 商品排行/Top 商品：`store`、`dateType/dateRange`、`orderBy`、`topN`。
- 单品概览/趋势/流量/详情：再需要明确 `itemId`。
- `dateType` 支持 `day`、`recent7`、`recent30`；默认近 7 天。
- 用户点名店铺、商品、指标或周期时原样保留；缺少影响目标的关键值时一次性询问。

## 主线

1. `sycmcli stores list` 唯一解析店铺；检查绑定身份。
2. 排行使用 `sycmcli shop items --all` 取得完整分页，再按用户指定指标排序；不得把接口默认顺序当作用户要求的排行。
3. 单品查询按意图执行 `shop-item overview|diagnose|detail|flow|gallery`；明确周期时传 `--date-range`。
4. 对返回的店铺、itemId、周期、分页完整性和指标字段做产出后校验。
5. 返回数据表、原始平台值、比较值、完整性和缺口。需要分析时将结果交给对应独立 Skill，例如 `item-traffic-analysis` 或 `comprehensive-product-data-analysis`。

## 输出

`store`、`queryType`、`dateRange`、`itemId`、`recordCount`、`returnedCount`、`complete`、`items/metrics/modules`、`sourceCommands`、`dataGaps`。

## 异常与边界

- 登录/滑块：打开该店铺可见浏览器，用户完成后重试一次。
- 身份不符立即停止；不切换或覆盖绑定。
- 只读；不创建推广、不改商品；不调用旧 `sycm-agent`。
- `null` 和脱敏区间保持原样；完成后清理临时经营数据。
