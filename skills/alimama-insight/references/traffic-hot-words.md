# 热门推荐词

获取店铺推荐的热门搜索关键词（最多 10 个）。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1524)
- **来源**: 流量解析 — 热门推荐词

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| (无) | — | — | — | 无需额外参数，moduleParams 固定为 `{ needGray: true }` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| hotWords | array | 热门关键词列表（最多 10 个） |
| hotWords[].keyword | string | 关键词文本 |
| hotWords[].value | string | 关键词值/标识 |

## 调用示例

```
eval-merchant-script(script="scripts/traffic-hot-words.js")
```
