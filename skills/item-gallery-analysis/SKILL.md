---
name: item-gallery-analysis
description: 分析指定淘宝或天猫商品的主图与视频素材表现，包括曝光、互动、支付、转化和流失。适用于“哪张主图表现最好”“主图有没有拖累转化”“分析商品图片和视频效果”等请求。
---

# 商品主图与视频素材分析

本 Skill 负责素材效果口径、样本门槛、排序、问题判断和行动建议。真实取数、店铺身份校验、登录恢复与多店铺浏览器由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.item.gallery.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若目录未提供，执行 `sycmcli skill source --json` 获取 canonical source。完整读取当前 `SKILL.md` 后执行。
- 兼容判断：确认版本不低于 `0.4.0`，并检查 `sycmcli capabilities --json` 声明 `sycm.item.gallery.read`。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`。

## 输入

- `store`：店铺别名或显示名称。用户点名时必须唯一匹配。
- `itemId`：商品 ID。优先从用户或当前商品上下文取得；无法唯一确定时请用户提供。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `contentType`：可选，`gallery` 或 `video`；默认分析全部。
- `limit`：每类展示数量，默认 5，范围 1～20。

## 主线

### 1. 校验依赖、店铺和商品

1. 加载当前 `sycmcli` Skill，验证版本和必需能力。
2. 运行 `sycmcli stores list`，将店铺名称解析为唯一别名。
3. 确认商品 ID 来自用户或当前商品上下文，不得猜测。

### 2. 获取全部素材表现

创建权限受限的临时目录，先运行：

```bash
sycmcli shop-item gallery --store <alias> --item-id <id> --date-type <type> --page 1 --page-size 100 --out <temp>/gallery.json
```

用户提供明确周期时追加 `--date-range <START|END>`；只分析图片或视频时追加 `--content-type gallery|video`。

检查 `recordCount` 与 `materials.length`。若记录数超过本页返回量，继续按页获取并合并，直到完整或平台返回空页；不能用第一页代表全部素材。

### 3. 生成确定性分析底稿

完整集合写入同一结构后运行：

```bash
node scripts/analyze.mjs --input <temp>/gallery.json --store <alias> --limit <N>
```

脚本输出：

- 曝光最高素材；
- 达到有效样本门槛后的高支付转化素材；
- 高流失素材；
- 图片与视频的分组摘要；
- 数据驱动的行动建议。

曝光人数、互动人数和支付人数在不同素材之间可能重叠，不能把素材行直接相加当作商品总人数。

### 4. 业务解读

1. 先说明周期、素材总数、图片/视频数量和完整性。
2. 展示高曝光、高转化和高流失素材的类型、素材标识、核心指标及平台比较值。
3. 高转化判断必须同时展示曝光样本；低样本素材只称“待验证信号”。
4. 若某素材兼具高曝光和高流失，优先列为修复对象。
5. 行动建议最多 3 条，每条写明数据依据、动作和下周期观察指标。

接口返回的是效果数据，不包含素材画面语义。用户需要诊断文案、构图、卖点或视觉一致性时，必须先取得真实图片或视频画面并使用宿主明确提供的视觉能力；不能根据效果数字猜测画面内容。

## 输出契约

```json
{
  "store": "店铺别名",
  "itemId": "商品ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "completeness": {},
  "typeSummary": [],
  "materials": [],
  "topExposure": [],
  "highConversion": [],
  "highLoss": [],
  "actions": [],
  "dataGaps": []
}
```

面向用户时使用简洁中文和小表格，不必原样输出 JSON。素材 URL 可用于定位素材，但不应在无视觉检查时描述其画面。

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 素材为空：返回真实周期和空结果，不虚构素材或指标。
- `null`：保留缺失语义，不参与排序、样本门槛或计算。
- 分页不完整：明确列出已取数量、总记录数和停止原因，不给出“全部素材”结论。

## 边界

- 只读，不修改、替换、生成或发布素材。
- 效果相关性不等于画面因果；没有位置、流量来源或实验分组时，不把差异归因于具体设计元素。
- 完成后删除临时经营数据。

## 验收

- 店铺、商品与周期可追溯，素材集合完整性明确。
- 素材指标保留平台值和比较值，`null` 未被改写为 0。
- 高转化结论通过样本门槛，高曝光与高流失风险可回指到素材。
- 没有根据数字臆测画面内容，建议不超过 3 条。
- 临时经营数据已清理。
