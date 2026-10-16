# 获取本品核心指标

获取本品核心指标（UV/PV/支付金额/支付转化率等），通过 selfItemId 定位本品。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/mq/rivalItem/analysis/getCoreIndexes.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `selfItemId` | string | 是 | `692941946548` | 本店商品 ID |
| `dateType` | string | 是 | `recent7` | 时间维度（recent7/recent30/day） |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 YYYY-MM-DD|YYYY-MM-DD |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data` | object | 核心指标数据（UV/PV/支付金额/支付转化率等） |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/get-core-indexes.js" \
  --args '{"selfItemId":"692941946548","dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `code 非 0` | API 返回错误码 | 检查 selfItemId 是否有效，检查登录态是否过期 |
| `data 为空` | 商品无数据或日期范围无效 | 确认商品 ID 正确，调整 dateRange |

## 注意事项

- dateRange 格式为 YYYY-MM-DD|YYYY-MM-DD
- 需先在浏览器完成淘宝登录
