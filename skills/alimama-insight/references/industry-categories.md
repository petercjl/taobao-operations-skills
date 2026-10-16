# 行业品类列表

获取商家可用的一级品类列表。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1638)
- **来源**: 行业解析 — 品类选择器

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| _(无)_ | | | 无需业务参数，bizCode 固定为 `"onebpSearch"` |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| categories[].cateLevel1Id | string | 一级品类 ID |
| categories[].cateLevel1Name | string | 一级品类名称 |

## 调用示例

```
eval-merchant-script(script="scripts/industry-categories.js")
```
