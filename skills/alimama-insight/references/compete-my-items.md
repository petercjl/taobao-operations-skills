# 我的商品排名

获取当前店铺商品在品类内的竞争流量指标排名。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=5958)
- **来源**: 竞争分析 — 我的商品

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| catelv2Id | string | 是 | 二级品类 ID |
| startTime | string | 否 | 开始日期 (YYYY-MM-DD)，默认近7天 |
| endTime | string | 否 | 结束日期 (YYYY-MM-DD) |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| catelv2Id | string | 查询的二级品类 ID |
| items[].itemId | string | 商品 ID |
| items[].title | string | 商品标题 |
| items[].charge | number | 花费 |
| items[].impression | number | 展现量 |
| items[].ctr | number | 点击率 |
| items[].ecpc | number | 平均点击花费 |
| items[].flowOutCount | number | 竞争流出次数 |
| items[].flowInCount | number | 竞争流入次数 |

## 调用示例

```
eval-merchant-script(script="scripts/compete-my-items.js", args={"catelv2Id": "50011740"})
```

## 备注

- `catelv2Id` 可通过 `compete-default-category.js` 获取
