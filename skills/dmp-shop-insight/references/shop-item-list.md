# 查询全店商品列表

分页查询全店商品表现，并按关键词、类目、生命周期、潜力、价格带和标签筛选，只读。图片中的点击、转化、ROI、连带购买等指标主要从每个商品的 `indicators[]` 按 key 提取。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/shop/item/list`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `endDate` | string | 是 | — | 来自 `shop-date-range.maxDate` |
| `period` | string | 否 | `"30"` | `"1"`、`"7"` 或 `"30"` |
| `page` | number | 否 | `1` | 正整数 |
| `pageSize` | number | 否 | `10` | `1–100` |
| `keyword` | string | 否 | `""` | 用户输入的商品关键词 |
| `lifeStageCodes` | string | 否 | — | 生命周期代码，英文逗号分隔 |
| `potentialLevels` | string | 否 | `""` | `"1"`、`"2"`、`"3"`，可逗号分隔 |
| `priceLevels` | string | 否 | `""` | 价格带代码，英文逗号分隔 |
| `itemLabels` | string | 否 | — | 来自 `shop-label-list.labels[].id` |
| `cate1Id/cate2Id/leafCateId` | string | 否 | — | 来自 `shop-std-cate.categories[]` |
| `orderIndicator` | string | 否 | — | 排序指标 |
| `orderType` | string | 否 | — | `asc` 或 `desc` |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `pager.total` | number | 商品总数 |
| `items[].id` | number | 商品 ID |
| `items[].name` | string | 商品标题 |
| `items[].pictUrl` | string | 商品图片 |
| `items[].lifeCycleList[].lifeCycleDesc` | string | 生命周期阶段 |
| `items[].gmv` | number | 商品支付金额顶层值 |
| `items[].ipv` | number | 商品浏览量顶层值 |
| `items[].charge` | number | 推广花费顶层值 |
| `items[].indicators[].key` | string | 指标 key，如 `alipayAmt`、`taobaoSearchClkCnt` |
| `items[].indicators[].value` | number | 本商品对应指标值 |
| `items[].indicators[].peerValue` | number | 同行同层基准原始值 |
| `items[].indicators[].generalizedPeerValue` | string | 同行同层基准模糊展示值 |
| `error` | string | 失败时的错误摘要 |

## 图片指标读取

从 `items[].indicators[]` 中按以下 key 读取目标数据：

| 指标 | key | 说明 |
|---|---|---|
| 支付金额 | `alipayAmt` | 商品累计支付金额 |
| 支付金额占比 | `alipayAmtPortion` | 支付金额占全店比例 |
| IPV | `ipv` | 商品详情页浏览量 |
| 自然点击量 | `freeDomainClkCnt` | 免费自然渠道点击 |
| 营销推广点击量 | `allsiteAdClkCnt` | 营销推广总点击 |
| 淘宝推荐点击量 | `taobaoRecClkCnt` | 淘宝推荐渠道点击 |
| 淘宝搜索点击量 | `taobaoSearchClkCnt` | 淘宝搜索渠道点击 |
| 免费搜索点击率 | `searchCtr` | 免费搜索 CTR，可结合同行同层基准 |
| 收加率 | `colAndCartRatio` | 收藏加购率 |
| 支付转化率 | `payRatio` | 支付转化率 |
| 笔单价 | `avgAlipayAmt` | 平均客单/笔单金额 |
| 营销推广 ROI | `roi` | 推广投入产出比 |
| 连带购买量 | `relatedAlipayCnt` | 连带成交件数/量 |
| 连带购买率 | `relatedAlipayRate` | 连带购买比例 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-item-list.js" \
  --args '{"endDate":"2026-08-05","period":"30","type":"1","lifeStageCodes":"1","page":1,"pageSize":10}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 商品为空 | 日期无数据或筛选过严 | 核对 `maxDate`，逐步放宽筛选 |
| 分页失败 | 页码或分页大小不合法 | 使用正整数和 `1–100` 的分页大小 |

## 注意事项

- 多个 ID 使用英文逗号分隔。
- 不把空列表解释为商品数为零，先区分无数据、无权限和筛选无匹配。
- 图片指标不是固定顶层字段时，优先在 `items[].indicators[]` 中按 `key` 查找。
