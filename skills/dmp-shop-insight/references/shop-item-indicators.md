# 获取商品列表可用指标

获取商品列表列的指标名称、字段 key 与默认展示配置，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/shop/item/indicators`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `type` | string | 否 | `"1"` | `"1"`=全店洞察，`"2"`=品类，`"4"`=推广 |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `indicators[].name` | string | 指标展示名称 |
| `indicators[].key` | string | 指标字段 key |
| `indicators[].default` | boolean | 是否默认展示 |
| `indicators[].parentKey` | string | 父级指标 key |
| `error` | string | 失败时的错误摘要 |

## 图片指标字段映射

这些指标来自本轮录制的 `shop-item-indicators` 返回值，可用于读取 `shop-item-list.items[].indicators[]` 中的同名 `key`。

| 指标 | key | 分组 |
|---|---|---|
| 支付金额 | `alipayAmt` | 成交表现 |
| 支付金额占比(占全店) | `alipayAmtPortion` | 成交表现 |
| IPV | `ipv` | 流量规模 |
| 自然点击量 | `freeDomainClkCnt` | 营销表现 |
| 营销推广点击量 | `allsiteAdClkCnt` | 营销表现 |
| 淘宝推荐点击量 | `taobaoRecClkCnt` | 营销表现 |
| 淘宝搜索点击量 | `taobaoSearchClkCnt` | 营销表现 |
| 免费搜索点击率 | `searchCtr` | 转化能力 |
| 收加率 | `colAndCartRatio` | 转化能力 |
| 支付转化率 | `payRatio` | 转化能力 |
| 笔单价 | `avgAlipayAmt` | 价格力 |
| 营销推广 ROI | `roi` | 营销表现 |
| 连带购买量 | `relatedAlipayCnt` | 长效价值力 |
| 连带购买率 | `relatedAlipayRate` | 长效价值力 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-item-indicators.js" \
  --args '{"type":"1"}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `type` 无效 | 使用了未支持场景 | 全店洞察固定使用 `"1"` |

## 注意事项

- 指标 key 可用于解释商品列表字段、选择排序指标，或从商品明细的 `indicators[]` 中提取图片里的目标数据。
