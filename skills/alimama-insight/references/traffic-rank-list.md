# 搜索词榜单

获取 8 个关键词排行榜（飙升词、热搜词、转化词等），支持按品类筛选。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1463) + `POST /cube/triggerDataFlowById.json`
- **来源**: 流量解析 — 搜索词榜单卡片
- **协议**: 两阶段调用 — 先获取模块模板和 dataFlowId 列表，再通过 triggerDataFlowById 获取实际关键词数据，最后解析 `##result[N]##` 模板引用

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| cateLevel1Id | string | 否 | — | 一级品类 ID（来自 traffic-shop-categories） |
| cateLevel2Id | string | 否 | — | 二级品类 ID（来自 traffic-shop-categories） |
| cateLevel2Name | string | 否 | — | 二级品类名称（来自 traffic-shop-categories） |
| needGray | boolean | 否 | `true` | 是否需要灰度 |
| isWordRankShow | number | 否 | `1` | 是否展示词榜 |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| dataFlowCount | number | 解析的 dataFlow 数量 |
| ranks | array | 榜单列表（最多 8 个 tab） |
| ranks[].name | string | 榜单名称（飙升词/热搜词/转化词等） |
| ranks[].type | string | 榜单类型标识 |
| ranks[].keywords | array | 关键词列表 |
| ranks[].keywords[].keyword | string | 关键词文本 |
| ranks[].keywords[].keywordId | string | 关键词 ID |
| ranks[].keywords[].searchIndex | number | 搜索指数 |
| ranks[].keywords[].clickRate | number | 点击率 |
| ranks[].keywords[].conversionRate | number | 转化率 |
| ranks[].keywords[].marketAverageBid | number | 市场均价 |
| ranks[].keywords[].competitionIndex | number | 竞争指数 |
| ranks[].keywords[].onlineSearchIndex | number | 在线搜索指数 |

## 调用示例

```
eval-merchant-script(script="scripts/traffic-rank-list.js", args={"cateLevel1Id": "50011740", "cateLevel2Id": "50011743", "cateLevel2Name": "T恤"})
```

## 备注

- **dataFlow 机制**: 模块返回的 compExt.tabs[].list 可能是模板字符串 `##result[N]##`，需要通过 triggerDataFlowById 获取实际数据后按索引替换。dataFlow 请求需要传入与模块相同的 moduleParams，服务端据此返回对应品类的关键词数据。
- **品类筛选**: cateLevel1Id、cateLevel2Id、cateLevel2Name 三个参数需要同时传入才能正确筛选。这些值从 traffic-shop-categories 脚本获取。
- **无参数调用**: 不传品类参数时返回全店维度的关键词榜单。
