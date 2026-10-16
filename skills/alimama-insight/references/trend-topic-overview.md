# 趋势主题概览

获取某个趋势主题的概览信息，包括热点数据、人群评估和解读。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=15884)
- **来源**: 趋势速递 — 主题详情页概览区域

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| topicId | string | 是 | — | 主题 ID（来自 trend-topic-list） |
| topicName | string | 否 | `""` | 主题名称 |
| topicCate | string | 否 | `""` | 主题品类 |
| brandSource | string | 否 | `""` | 品牌来源 |
| brandType | string | 否 | `""` | 品牌类型 |
| tab | string | 否 | `"member_item_search"` | tab 类型 |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| topicId | string | 主题 ID |
| topicName | string | 主题名称 |
| banner | string | 主题 banner 图片 URL |
| hotData | object | 热点数据 |
| hotData.hotValue | number | 热度值 |
| hotData.investmentPlan | number | 投放计划数 |
| hotData.ppc | number | 平均点击单价 |
| hotData.crowdSize | number | 人群规模 |
| crowdAssessment | object | 热点人群评估 |
| crowdAssessment.myCrowdSize | number | 我的人群规模 |
| crowdAssessment.otherCrowdSize | number | 竞品人群规模 |
| crowdAssessment.crowdSize | number | 总人群规模 |
| interpretation | string | 主题解读文本 |

## 调用示例

```
eval-merchant-script(script="scripts/trend-topic-overview.js", args={"topicId": "123456", "topicName": "防晒"})
```
