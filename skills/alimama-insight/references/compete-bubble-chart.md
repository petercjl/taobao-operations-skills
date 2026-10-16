# 市场渗透率气泡图

获取四象限气泡图数据，展示关键词的搜索指数与推广组数分布。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=5686)
- **来源**: 竞争分析 — 市场渗透率四象限气泡图

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| catelv2Id | string | 是 | 二级品类 ID |
| wordType | string | 否 | 词类型，默认 `"E"`。B=店铺专有词, E=类目精准词, S=行业热门词, T=趋势机会词 |
| dataType | number | 否 | 数据类型，默认 `1` |
| startTime | string | 否 | 开始日期 (YYYY-MM-DD)，默认近7天 |
| endTime | string | 否 | 结束日期 (YYYY-MM-DD) |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| catelv2Id | string | 查询的二级品类 ID |
| chartData[].keyword | string | 关键词 |
| chartData[].searchIndex | number | 搜索指数 |
| chartData[].adgroupCount | number | 推广组数量 |
| chartData[].quadrant | string | 所在象限标识 |

## 调用示例

```
eval-merchant-script(script="scripts/compete-bubble-chart.js", args={"catelv2Id": "50011740"})
```

## 备注

- `catelv2Id` 可通过 `compete-default-category.js` 获取
- 气泡图横轴为搜索指数，纵轴为推广组数量，按象限划分竞争态势
