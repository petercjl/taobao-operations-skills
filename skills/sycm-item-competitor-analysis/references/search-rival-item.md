# 搜索竞品商品

按关键词搜索竞品商品列表，返回 itemId/name/uv/payByrCnt 等字段。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/ci/free/index/rival/item/search.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `dateType` | string | 是 | `recent7` | 时间维度 |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data[].itemId` | string | 竞品商品 ID |
| `data[].name` | string | 竞品商品标题 |
| `data[].index.uv.value` | string | 竞品访客数（区间值） |
| `data[].index.payByrCnt.value` | string | 竞品支付买家数（区间值） |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/search-rival-item.js" \
  --args '{"dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `data 为空数组` | 无匹配竞品 | 调整搜索条件或日期范围 |
| `code 非 0` | API 返回错误码 | 检查登录态是否过期 |

## 注意事项

- 返回的竞品 itemId 用于后续流程的 rivalItem1Id 参数
