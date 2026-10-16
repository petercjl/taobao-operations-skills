# 热点关键词列表

获取某个趋势主题下的热点关键词列表，包含搜索指数、趋势指数、预估 PPC 等。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=15899) + `POST /cube/triggerDataFlowById.json`
- **来源**: 趋势速递 — 主题详情页关键词区域
- **协议**: 两阶段调用 — 先获取模块模板和 dataFlowId 列表，再通过 triggerDataFlowById 获取实际关键词数据，最后解析 `##path.to.field##` 模板引用

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
| keywordCount | number | 关键词数量 |
| keywords | array | 关键词列表（已去重） |
| keywords[].word | string | 关键词文本 |
| keywords[].searchIndex | number | 搜索指数 |
| keywords[].trendIndex | number | 趋势指数 |
| keywords[].commissioningIndex | number | 投放指数 |
| keywords[].estimatePpc | number | 预估点击单价 |
| keywords[].estimateGmv | number | 预估 GMV |

## 调用示例

```
eval-merchant-script(script="scripts/trend-topic-keywords.js", args={"topicId": "123456", "topicName": "防晒"})
```

## 备注

- **dataFlow 模板解析**: 模块返回的 compExt.list 可能是模板字符串如 `##topicDetailInfo.wordList##`，而非实际数据。脚本通过 triggerDataFlowById 获取 dataFlow 结果（结构为 `resultList[0] = { topicDetailInfo: { wordList: [...], topWordList: [...] } }`），然后按 `.` 分隔路径逐级导航到目标数组完成替换。
- **去重**: 返回结果按 word 字段去重，避免来自不同 compExt 来源的重复关键词。
