# 趋势主题排行列表

获取趋势速递的主题排行列表，支持按 tab 切换货品推广/全网搜索/周期趋势维度。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=6687)
- **来源**: 趋势速递 — 主题排行页
- **bizCode**: `"onebpSearch"`

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tab | string | 否 | `"member_item_search"` | 维度切换: `"member_item_search"` (货品推广) / `"online_search"` (全网搜索) / `"period_search"` (周期趋势) |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| tab | string | 当前 tab |
| topicCount | number | 主题数量 |
| topics | array | 主题列表 |
| topics[].topicId | string | 主题 ID |
| topics[].topicName | string | 主题名称 |
| topics[].topicCate | string | 主题品类 |
| topics[].topicType | string | 主题类型 |
| topics[].brandSource | string | 品牌来源 |
| topics[].capacity | number | 容量/热度值 |
| topics[].weekChangeRatio | number | 周变化率 |
| topics[].weekChangeRatioPer | string | 周变化率百分比 |
| topics[].relationScore | number | 相关度分数 |
| topics[].topicSource | string | 主题来源 |
| topics[].brandType | string | 品牌类型 |

## 调用示例

```
eval-merchant-script(script="scripts/trend-topic-list.js", args={"tab": "member_item_search"})
```
