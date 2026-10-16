# 今日流量预测

获取指定一级品类的今日流量预测 KPI 及小时级展现指数趋势。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1749 KPI + moduleId=1781 图表)
- **来源**: 行业解析 — 今日流量预测卡片

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| cateLevel1Id | string | 是 | 一级品类 ID |
| startTime | string | 否 | 日期 (YYYY-MM-DD)，默认今天 |
| vsStartTime | string | 否 | 对比日期 (YYYY-MM-DD)，默认昨天 |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| cateLevel1Id | string | 查询的一级品类 ID |
| date | string | 当前日期 |
| vsDate | string | 对比日期 |
| hourlyTraffic[].hour | string | 小时时间点 |
| hourlyTraffic[].currentIndex | number | 当前展现指数 |
| hourlyTraffic[].historicalIndex | number | 对比日展现指数 |
| advice | string | AI 投放建议文本 |

## 调用示例

```
eval-merchant-script(script="scripts/industry-traffic-forecast.js", args={"cateLevel1Id": "50011740"})
```

## 备注

- `cateLevel1Id` 可通过 `industry-categories.js` 获取
- 同时请求两个 moduleId (1749+1781)，并行获取 KPI 和图表数据
