# 流量来源 QZT 参与度

获取流量来源 QZT 参与度数据。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/rivalItem/getFlowsource/qzt/participate/free.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `selfItemId` | string | 是 | `692941946548` | 本店商品 ID |
| `rivalItem1Id` | string | 是 | `861895294478` | 竞品商品 ID |
| `dateType` | string | 是 | `recent7` | 时间维度 |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data` | object | QZT 参与度数据 |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/get-flowsource-qzt.js" \
  --args '{"selfItemId":"692941946548","rivalItem1Id":"861895294478","dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `data 为空` | 无 QZT 参与度数据 | 确认商品 ID 和日期范围有效 |
| `code 非 0` | API 返回错误码 | 检查登录态是否过期 |

## 注意事项

- 需同时传入 selfItemId 和 rivalItem1Id
