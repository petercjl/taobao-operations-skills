# 行业优秀新品

获取行业标杆商品列表，含展现和成交环比等级。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=5961)
- **来源**: 竞争分析 — 行业优秀新品

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| catelv2Id | string | 是 | 二级品类 ID |
| startTime | string | 否 | 开始日期 (YYYY-MM-DD)，默认近7天 |
| endTime | string | 否 | 结束日期 (YYYY-MM-DD) |
| custLevel | string | 否 | 客单价档位筛选，默认 `"不限"` |
| cmpId | string | 否 | 竞品类型 ID，默认 `"3"` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| catelv2Id | string | 查询的二级品类 ID |
| items[].itemId | string | 商品 ID |
| items[].title | string | 商品标题 |
| items[].impressionWowGrade | number | 展现环比等级 |
| items[].alipayCntWowGrade | number | 成交笔数环比等级 |
| items[].recInfo | string | 推荐理由 |

## 调用示例

```
eval-merchant-script(script="scripts/compete-excellent-items.js", args={"catelv2Id": "50011740"})
```

## 备注

- `catelv2Id` 可通过 `compete-default-category.js` 获取
- `custLevel` 可用于按客单价区间筛选标杆商品
