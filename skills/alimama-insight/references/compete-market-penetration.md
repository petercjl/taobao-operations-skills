# 市场渗透率表格

按词类型对比店铺与行业的市场渗透率等级。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=5589)
- **来源**: 竞争分析 — 市场渗透率

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
| wordType | string | 当前词类型 |
| shop[].wordType | string | 词类型代码 |
| shop[].wordTypeName | string | 词类型名称 |
| shop[].marketShareGrade | number | 店铺渗透率等级 |
| shop[].marketShareGradeAv | number | 店铺渗透率均值 |
| compare[].wordType | string | 词类型代码 |
| compare[].wordTypeName | string | 词类型名称 |
| compare[].marketShareGrade | number | 行业渗透率等级 |
| compare[].marketShareGradeAv | number | 行业渗透率均值 |
| compareText | string | 对比结论文本 |
| minMarketShareGrade | number | 最低渗透率等级 |
| bestType | string | 最优词类型 |

## 调用示例

```
eval-merchant-script(script="scripts/compete-market-penetration.js", args={"catelv2Id": "50011740"})
```

## 备注

- `catelv2Id` 可通过 `compete-default-category.js` 获取
