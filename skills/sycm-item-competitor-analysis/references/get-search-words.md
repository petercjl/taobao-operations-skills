# 入店搜索词

获取入店搜索词及对应指标（访客数/支付转化率/支付买家数）。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/mq/rivalItem/analysis/getSearchWords.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `selfItemId` | string | 是 | `692941946548` | 本店商品 ID |
| `indexCode` | string | 是 | `uv` | 指标维度（uv/payRate/payByrCnt） |
| `dateType` | string | 是 | `recent7` | 时间维度 |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 |
| `page` | number | 否 | `1` | 页码 |
| `pageSize` | number | 否 | `30` | 每页条数 |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data.selfItem[].keyword.value` | string | 搜索关键词 |
| `data.selfItem[].uv.value` | number | 本品搜索词访客数 |
| `data.selfItem[].payRate.value` | number | 本品搜索词支付转化率 |
| `data.selfItem[].payByrCnt.value` | number | 本品搜索词支付买家数 |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/get-search-words.js" \
  --args '{"selfItemId":"692941946548","indexCode":"uv","dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `data.selfItem 为空` | 无入店搜索词数据 | 确认 selfItemId 有效，调整日期范围 |
| `code 非 0` | API 返回错误码 | 检查登录态是否过期 |

## 注意事项

- 只返回本品搜索词数据
- 切换 indexCode 获取不同维度的搜索词排名
