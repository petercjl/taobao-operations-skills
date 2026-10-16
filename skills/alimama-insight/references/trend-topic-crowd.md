# 人群品类偏好

获取某个趋势主题下的人群品类偏好分布，对比我的店铺与竞品的人群占比。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=4273)
- **来源**: 趋势速递 — 主题详情页人群分析区域

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
| crowdCategories | array | 人群品类偏好列表（已去重） |
| crowdCategories[].cateName | string | 品类名称 |
| crowdCategories[].ratio | number | 占比 |
| crowdCategories[].myShopRatio | number | 我的店铺占比 |
| crowdCategories[].competitionRatio | number | 竞品占比 |
| crowdCategories[].myScale | number | 我的店铺规模 |
| crowdCategories[].competitionScale | number | 竞品规模 |

## 调用示例

```
eval-merchant-script(script="scripts/trend-topic-crowd.js", args={"topicId": "123456", "topicName": "防晒"})
```

## 备注

- 数据来源有两种路径: 优先从 compExt.resultList 获取，如果为空则回退到 compExt.chartGroup 饼图数据。
