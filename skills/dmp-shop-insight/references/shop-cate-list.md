# 查询叶子类目列表

分页查询叶子类目的 GMV、花费、商品数和机会潜力评分，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/cate/list`
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
| `orderIndicator` | string | 否 | — | 如 `shopCateGmv`、`itemCount`、`charge` |
| `orderType` | string | 否 | — | `asc` 或 `desc` |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `pager.total` | number | 类目总数 |
| `categories[].cateId` | number | 叶子类目 ID |
| `categories[].cateName` | string | 叶子类目名称 |
| `categories[].shopCateGmv` | number | 类目 GMV |
| `categories[].charge` | number | 推广花费 |
| `categories[].score` | number | 机会潜力评分 |
| `error` | string | 失败时的错误摘要 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-cate-list.js" \
  --args '{"endDate":"2026-08-05","period":"30","page":1,"pageSize":5}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 返回空列表 | 日期、周期无数据或筛选过严 | 核对 `maxDate` 和查询条件 |
| 分页参数失败 | 页码或分页大小越界 | 使用正整数和 `1–100` 的分页大小 |

## 注意事项

- 排序字段应来自业务需要，不要把未知字段直接透传。
