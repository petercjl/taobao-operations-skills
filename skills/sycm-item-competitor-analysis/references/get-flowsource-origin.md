# 流量来源（平铺）

获取流量来源平铺列表，支持 indexCode（uv/payRate/payByrCnt）切换维度。同时返回本品和竞品的支付转化率、访客数、支付买家数。

## API 信息

- Endpoint：`GET https://sycm.taobao.com/mc/rivaItem/analysis/getFlowSource/origin/v4/free.json`
- 协议：HTTP
- Scene：`https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `selfItemId` | string | 是 | `692941946548` | 本店商品 ID |
| `rivalItem1Id` | string | 是 | `861895294478` | 竞品商品 ID |
| `indexCode` | string | 是 | `uv` | 指标维度（uv=访客数/payRate=支付转化率/payByrCnt=支付买家数） |
| `dateType` | string | 是 | `recent7` | 时间维度 |
| `dateRange` | string | 是 | `2026-08-05|2026-08-11` | 日期范围 |
| `page` | number | 否 | `1` | 页码 |
| `pageSize` | number | 否 | `30` | 每页条数 |
| `order` | string | 否 | `desc` | 排序方向（desc/asc） |
| `orderBy` | string | 否 | `` | 排序字段（默认跟随 indexCode） |
| `flowBizType` | string | 否 | `classic` | 流量业务类型（固定） |
| `pageType` | string | 否 | `item` | 页面类型（固定） |
| `marketVersion` | string | 否 | `free` | 市场版本（固定） |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `data[].pageName.value` | string | 渠道名称（搜索/推荐/淘宝直播/淘金币/芭芭农场等） |
| `data[].selfItemPayRate.value` | number | 本店商品支付转化率（小数，如 0.0168 = 1.68%） |
| `data[].rivalItem1PayRate.value` | string | 竞品1支付转化率（区间值，如 7.5% ~ 10%） |
| `data[].selfItemUv.value` | number | 本店商品访客数 |
| `data[].rivalItem1Uv.value` | string | 竞品1访客数（区间值） |
| `data[].selfItemPayByrCnt.value` | number | 本店商品支付买家数 |
| `data[].rivalItem1PayByrCnt.value` | string | 竞品1支付买家数（区间值） |
| `traceId` | string | 链路追踪 ID |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/get-flowsource-origin.js" \
  --args '{"selfItemId":"692941946548","rivalItem1Id":"861895294478","indexCode":"payRate","dateType":"recent7","dateRange":"2026-08-05|2026-08-11"}' \
  --scene "https://sycm.taobao.com/mc/free/ci_item?activeKey=itemCompare&dateRange=2026-07-07%7C2026-08-05&dateType=recent30&selfItem=692941946548&rivalItem1=861895294478&rivalItem2=&ciShop=flow" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `data 为空数组` | 无流量来源数据 | 确认商品 ID 和日期范围有效 |
| `code 非 0` | API 返回错误码 | 检查 selfItemId 和 rivalItem1Id 是否有效 |
| `selfItemPayRate 缺失` | indexCode 未传 payRate | 确认 indexCode 参数设为 payRate |

## 注意事项

- 获取支付转化率时 indexCode 必须传 payRate
- orderBy 默认跟随 indexCode 值
- 与 get-flowsource-v4 的区别：origin 返回平铺列表，v4 返回树形结构含 children
