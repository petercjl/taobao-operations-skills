# 我的收藏词

获取用户收藏的关键词监控列表，包含搜索指数、点击指数、竞争指数等。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1464)
- **来源**: 流量解析 — 我的收藏词

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| (无) | — | — | — | 无需额外参数，bizCode 固定为 `"universalBP"` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | boolean | 请求是否成功 |
| favorites | array | 收藏词列表 |
| favorites[].keyword | string | 关键词文本 |
| favorites[].searchIndex | number | 搜索指数 |
| favorites[].clickIndex | number | 点击指数 |
| favorites[].competitionIndex | number | 竞争指数 |

## 调用示例

```
eval-merchant-script(script="scripts/traffic-favorites.js")
```
