# 二级品类列表

获取指定一级品类下的二级品类列表。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1640)
- **来源**: 行业解析 — 品类选择器（二级）

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| cateLevel1Id | string | 是 | 一级品类 ID |
| cateLevel1Name | string | 否 | 一级品类名称，默认空字符串 |
| dateType | string | 否 | 时间周期，默认 `"7"` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| subcategories[].cateLevel2Id | string | 二级品类 ID |
| subcategories[].cateLevel2Name | string | 二级品类名称 |

## 调用示例

```
eval-merchant-script(script="scripts/industry-subcategories.js", args={"cateLevel1Id": "50011740"})
```

## 备注

- `cateLevel1Id` 可通过 `industry-categories.js` 获取
