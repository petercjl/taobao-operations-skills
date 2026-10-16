# 获取全店洞察可用日期范围

获取全店洞察数据的最早和最晚可用日期，只读。

## API 信息

- Endpoint：`GET https://dmp.advgateway.taobao.com/api/goods/shop/dateRange`
- 协议：HTTP
- Scene：`https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=`
- 操作类型：只读

## 入参

无业务参数。

## 返回值

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | boolean | 业务调用是否成功 |
| `minDate` | string | 最早可用日期，格式 `YYYY-MM-DD` |
| `maxDate` | string | 最晚可用日期，供后续查询作为 `endDate` |
| `error` | string | 失败时的错误摘要 |

## 调用示例

```bash
api-anything eval \
  --script "<当前 SKILL 目录>/scripts/shop-date-range.js" \
  --args '{}' \
  --scene "https://dmp.taobao.com/index_new.html?spm=a2e3k.13920195.cf7687754.d46d8d2e4.4c8425ebdT0tpH#!/items/shop-insight?spm=" \
  --json
```

## 失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 缺少登录 Cookie 或 CSRF | 达摩盘未登录或运行时未加载 | 在目标页面完成登录并重试 |
| `maxDate` 为空 | 当前帐号无可用数据 | 说明无数据，不继续日期型查询 |

## 注意事项

- 日期型脚本应优先使用本接口的 `maxDate`，不要猜测最新日期。
