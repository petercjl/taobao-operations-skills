# 获取标准叶子类目树

获取一级、二级和叶子类目的扁平层级关系，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/dmp/shop/std/cate`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

| 参数 | 类型 | 必填 | 默认值 | 来源与说明 |
|---|---|---:|---|---|
| `cateModel` | number | 否 | `2` | 叶子类目模式 |
| `filterModel` | number | 否 | `0` | 默认过滤模式 |

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `categories[].cate1Id/cate1Name` | number/string | 一级类目 |
| `categories[].cate2Id/cate2Name` | number/string | 二级类目 |
| `categories[].leafCateId/leafCateName` | number/string | 叶子类目 |
| `error` | string | 失败时的错误摘要 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-std-cate.js" \
  --args '{"cateModel":2,"filterModel":0}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 类目为空 | 帐号无商品或权限不足 | 向用户说明，无需猜测类目 ID |

## 注意事项

- 选定的类目 ID 可传给 `shop-item-list` 的同名筛选参数。
