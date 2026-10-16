# 默认二级品类

获取当前商家的默认二级品类（竞争分析入口自动选中的品类）。

## API 信息

- **Endpoint**: `POST /cube/triggerDynamicModule.json` (moduleId=1523)
- **来源**: 竞争分析 — 初始化默认品类

## 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| _(无)_ | | | 无需业务参数 |

## 返回值

| 字段 | 类型 | 说明 |
|------|------|------|
| defaultCategory.cateLevel1Id | string | 一级品类 ID |
| defaultCategory.cateLevel1Name | string | 一级品类名称 |
| defaultCategory.cateLevel2Id | string | 二级品类 ID |
| defaultCategory.cateLevel2Name | string | 二级品类名称 |

## 调用示例

```
eval-merchant-script(script="scripts/compete-default-category.js")
```

## 备注

- 返回的 `cateLevel2Id` 可作为其他竞争分析脚本的入参
