# 店铺品类列表

获取店铺可筛选的品类列表，用于搜索词榜单（traffic-rank-list）的品类筛选参数。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=870)
- **来源**: 流量解析 — 品类筛选器

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| (无) | — | — | — | 无需额外参数，bizCode 固定为 `"universalBP"` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| categories | array | 品类列表 |
| categories[].cateLevel1Id | string | 一级品类 ID |
| categories[].cateLevel1Name | string | 一级品类名称 |
| categories[].cateLevel2Id | string | 二级品类 ID |
| categories[].cateLevel2Name | string | 二级品类名称 |
| categories[].shopAlipayRate | number | 店铺支付转化率 |

## 调用示例

```
eval-merchant-script(script="scripts/traffic-shop-categories.js")
```
