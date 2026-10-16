# 查询店铺总览

查询全店商品数、GMV、IPV、支付转化率与生命周期分布，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/shop/v3/overview`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `endDate` | string | 是 | — | 来自 `shop-date-range.maxDate`，格式 `YYYY-MM-DD` |
| `period` | string | 否 | `"30"` | `"1"`、`"7"` 或 `"30"` |
| `benchmark` | string | 否 | `"0"` | `"0"`=本店，`"1"`=同行对标 |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `itemCount` | number | 商品数 |
| `gmv` | number | 支付金额 |
| `ipv` | number | 商品详情页浏览量 |
| `paidCvr` | number | 支付转化率 |
| `newCount/potentialCount/hotCount/tailCount` | number | 各生命周期商品数 |
| `error` | string | 失败时的错误摘要 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-overview.js" \
  --args '{"endDate":"2026-08-05","period":"30","benchmark":"0"}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `endDate` 格式错误 | 未使用日期范围结果 | 先调用 `shop-date-range` |
| 业务返回无权限 | 帐号未开通货品洞察 | 向用户说明权限不足 |

## 注意事项

- 对比本店和同行时，两次查询必须使用相同的 `endDate` 与 `period`。
