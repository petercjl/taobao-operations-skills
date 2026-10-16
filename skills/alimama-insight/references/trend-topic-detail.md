# 主题详情（聚合）

一次调用并行获取趋势主题的概览、关键词、人群品类偏好三个维度的完整数据。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=15884, 15899, 4273) + `POST /cube/triggerDataFlowById.json`
- **来源**: 趋势速递 — 主题详情页全量数据
- **协议**: 内部并行调用三个模块: 概览 (15884) + 关键词 (15899 + dataFlow) + 人群 (4273)

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
| overview | object | 概览数据 |
| overview.banner | string | 主题 banner 图片 URL |
| overview.hotData | object | 热点数据 (hotValue, investmentPlan, ppc, crowdSize) |
| overview.crowdAssessment | object | 人群评估 (myCrowdSize, otherCrowdSize, crowdSize) |
| overview.interpretation | string | 主题解读文本 |
| keywords | array | 关键词列表（已去重） |
| keywords[].word | string | 关键词文本 |
| keywords[].searchIndex | number | 搜索指数 |
| keywords[].trendIndex | number | 趋势指数 |
| keywords[].commissioningIndex | number | 投放指数 |
| keywords[].estimatePpc | number | 预估点击单价 |
| keywords[].estimateGmv | number | 预估 GMV |
| crowdCategories | array | 人群品类偏好列表 |
| crowdCategories[].cateName | string | 品类名称 |
| crowdCategories[].ratio | number | 占比 |
| crowdCategories[].myShopRatio | number | 我的店铺占比 |
| crowdCategories[].competitionRatio | number | 竞品占比 |
| crowdCategories[].myScale | number | 我的店铺规模 |
| crowdCategories[].competitionScale | number | 竞品规模 |

## 调用示例

```
eval-merchant-script(script="scripts/trend-topic-detail.js", args={"topicId": "123456", "topicName": "防晒", "topicCate": "美妆"})
```

## 备注

- **聚合脚本**: 本脚本将 trend-topic-overview、trend-topic-keywords、trend-topic-crowd 三个独立脚本的逻辑合并为一次并行调用（`Promise.all`），适合需要一次性获取主题完整信息的场景。
- 如果只需要某一个维度的数据，建议使用对应的单独脚本以减少请求数。
