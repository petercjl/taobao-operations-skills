# 获取商品标签列表

获取商品列表可用的标签定义，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/shop/label/list`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

无业务参数。

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `labels[].id` | number | 标签 ID |
| `labels[].name` | string | 标签名称 |
| `labels[].desc` | string | 标签描述 |
| `error` | string | 失败时的错误摘要 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-label-list.js" \
  --args '{}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 标签为空 | 当前帐号没有可用标签 | 省略标签筛选并说明 |

## 注意事项

- 将选中的标签 ID 以英文逗号分隔后传给 `shop-item-list.itemLabels`。
