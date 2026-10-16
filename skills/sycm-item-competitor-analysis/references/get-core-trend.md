# 获取核心指标趋势

通过 indexCode 参数切换指标（uv/seGuidePayRate/motivatePayRate 等），获取本品/竞品趋势数据。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/mq/rivalItem/analysis/getCoreTrend.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `selfItemId` | string | 是 | `692941946548` | 本店商品 ID |
| `rivalItem1Id` | string | 是 | `861895294478` | 竞品商品 ID |
| `indexCode` | string | 是 | `uv` | 指标代码（uv/seGuidePayRate/motivatePayRate/payRate 等） |
| `dateType` | string | 是 | `recent7` | 时间维度 |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 |
| `device` | number | 否 | `0` | 设备类型（0=全部） |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data.rivalItem1[].statDay` | number | 竞品统计日期时间戳 |
| `data.rivalItem1[].uv` | string | 竞品访客数趋势 |
| `data.selfItem[].statDay` | number | 本品统计日期时间戳 |
| `data.selfItem[].uv` | number | 本品访客数趋势 |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/get-core-trend.js" \
  --args '{"selfItemId":"692941946548","rivalItem1Id":"861895294478","indexCode":"uv","dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `data.rivalItem1 为空` | rivalItem1Id 缺失或无效 | 确认 rivalItem1Id 参数已传入且为有效竞品 ID |
| `code 非 0` | API 返回错误码 | 检查 selfItemId 和 rivalItem1Id 是否有效 |

## 注意事项

- rivalItem1Id 为必填参数，缺失将导致竞品趋势数据为空
- 通过切换 indexCode 获取不同指标趋势
