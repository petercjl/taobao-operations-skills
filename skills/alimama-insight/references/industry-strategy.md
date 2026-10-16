# 行业策略分析

获取 AI 趋势洞察、AI 商机发现、行业活动动向等策略分析内容。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1932)
- **来源**: 行业解析 — 策略分析卡片

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| dateType | string | 否 | 时间周期，默认 `"7"`（近7天） |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| dateType | string | 当前查询时间周期 |
| industryFeature | string | 行业特征描述文本 |
| insights[].tag | string | 洞察类型 (AI趋势洞察/AI商机发现/行业活动动向) |
| insights[].title | string | 洞察标题 |
| insights[].text | string | 洞察详情文本 |
| insights[].category | string | 一级品类名称 |
| insights[].subcategory | string | 二级品类名称 |

## 调用示例

```
eval-merchant-script(script="scripts/industry-strategy.js", args={"dateType": "7"})
```
