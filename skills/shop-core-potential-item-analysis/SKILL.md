---
name: shop-core-potential-item-analysis
description: 从指定淘宝/天猫店铺的真实商品经营数据中识别核心品、潜力品和引流款。适用于“哪些商品值得重点推”“分析核心商品”“挖掘潜力爆品”“查看引流款”等请求。
---

# 核心品与潜力品分析

本 Skill 负责商品组合方法、店内分位数阈值、业务分类和行动建议。`sycmcli` 负责多店铺身份、登录恢复、全量商品取数和分页完整性。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- sycmcli 必需能力：`sycm.shop.items.read`
- 宿主能力：执行本地命令、创建受限临时目录、读取和删除临时 JSON 文件。
- 解析方式：从宿主公开目录按精确名称加载完整的 `sycmcli/SKILL.md`；目录未提供时执行 `sycmcli skill source --json`。运行 `sycmcli version` 和 `sycmcli capabilities --json` 验证版本及能力。
- 分析脚本：相对于本 Skill 目录的 `scripts/analyze.mjs`。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`；不得重建接口或调用旧 `sycm-agent`。

## 输入

- `store`：店铺别名或显示名称；用户点名时必须精确匹配。
- `dateType`：`day`、`recent7`、`recent30`，默认 `recent7`。
- `dateRange`：可选明确周期，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `direction`：`core`、`potential`、`both`；默认 `both`。
- `limit`：每个结果组展示数量，默认 20。
- `focus`：可选，用户特别关注的新品、流量、转化、退款或增长问题。

## 主线

### 1. 确认店铺与方向

1. 验证依赖版本和 `sycm.shop.items.read`。
2. 执行 `sycmcli stores list`，将用户指定的店铺显示名称解析为唯一别名。后续命令显式传入 `--store`。
3. 用户明确说核心品或潜力品时采用对应方向；没有偏好时执行 `both`，不额外打断用户。

### 2. 全量取数

在权限为仅当前用户可读的系统临时目录中生成输入文件，执行：

```bash
sycmcli shop items --store <alias> --date-type <day|recent7|recent30> --all --out <temp>/shop-items.json
```

明确周期时追加 `--date-range <START|END>`。不得把 Cookie、token 或浏览器存储写入文件。

检查：

- `ok=true`，店铺别名和绑定身份正确。
- `returnedCount=recordCount`，且 `stoppedBy` 为 `recordCount`、`shortPage` 或最后一页完成状态。
- `dateRange` 是实际报告周期。
- `null` 保持缺失，不能改写为 0。

若全量未完成，可继续分页恢复；仍不完整时允许输出核心商品的有限排序，但不得宣称已经完成全店潜力品或引流款筛选。

### 3. 确定性分类

运行：

```bash
node <skill-dir>/scripts/analyze.mjs --input <temp>/shop-items.json --direction <core|potential|both> --limit <N>
```

脚本使用同店铺、同周期商品分布计算阈值：

- 核心品：销售额不低于店内 P75，且支付买家数不低于店内 P50。
- 潜力品：尚未进入核心品，同时满足高流量和中位以上转化；或销售额达到店内 P50、平台销售额比较值为正，且流量/转化至少一项达到店内 P50。
- 引流款：尚未进入前两组，访客数达到店内 P75、转化低于店内 P50。
- 观察品：其余商品。

这些阈值用于店内相对筛选，不代表行业优秀线。`cycleCrc`、`syncCrc` 保留平台字段名；除非平台契约明确基期，不把它们擅自写成周环比或同比。

### 4. 业务解读

按用户方向回答，并把每个结论对应到商品和指标：

1. 核心品：说明销售贡献、买家、流量、转化和退款风险。
2. 潜力品：说明入选原因，是高质量流量还是平台比较值改善。
3. 引流款：说明流量优势与转化短板，不能直接称为潜力爆品。
4. 行动建议：每组最多 3 条，分别针对守盘、放量验证、转化修复或风险控制。

新品仅以平台返回的 `isNew` 为依据。没有成本、库存、广告消耗或毛利数据时，不下利润结论，也不直接建议大额投放。

### 5. 清理与交付

读取分析结果后删除临时业务数据文件。用户明确要求导出时，才将报告写到用户指定路径，并遵守不覆盖已有文件的规则。

默认直接返回：

- 店铺与周期
- 数据完整性
- 店内阈值
- 核心品、潜力品、引流款的数量和代表商品
- 每个商品的入选证据
- 最多 3 条优先行动
- 数据缺口

## 异常与恢复

- 登录、滑块或风控：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 完成；确认后重试。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切店。
- 分页中断：从未完成页继续，合并时按 `itemId` 去重。
- 数据为空：核对店铺、周期和权限后如实返回，不生成示例商品。
- 分析脚本失败：保留原始临时文件用于本轮诊断，修复后重跑；任务结束前删除。

## 验收

- 使用真实绑定店铺数据，全量结论具备完整性证据。
- 分类结果由本 Skill 的确定性脚本生成，可重复运行。
- 商品入选原因能够回指销售额、买家、访客、转化或平台比较字段。
- 没有把店内分位数描述成行业基准。
- 没有调用生意管家模型、旧 `sycm-agent` 或未注册接口。
