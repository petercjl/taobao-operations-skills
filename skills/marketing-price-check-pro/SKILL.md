---
name: marketing-price-check-pro
description: 批量核对本地价盘与淘宝线上标价、普惠券后价、一件预估价和最低到手价，输出可复核的差异与风险清单。适用于活动前价格检查与日常价盘巡检。
---

# 商品价格核验（进阶版）

本 Skill 以用户价盘文件为基准，保留现有 `scripts/price_check.py` 作为确定性处理入口；线上读取必须通过已声明的稳定能力，不在脚本中保存浏览器凭证。

## 输入

- 价盘文件（XLSX/CSV）与明确工作表；商品 ID、SKU（若按 SKU 核验）、本地目标价列为必需。
- `store`、核验日期、价格口径、允许误差；可选输出目录。
- 表格字段映射先预览并由用户确认；原文件只读。

## 主线

1. 按 `references/runtime-and-auth.md` 检查运行时和店铺身份，按 `references/excel-processing.md` 验证列与数据类型。
2. 创建独立工作副本，运行 `price_check.py` 的预检/分批流程；禁止覆盖源价盘。
3. 通过稳定已授权读取能力取得线上价格与时间戳；返回字段不完整时标记缺口，不猜测券后价。
4. 按商品/SKU 精确对齐，计算线上价与本地目标价差异，区分缺商品、缺 SKU、价格缺失、超阈值和口径不可比。
5. 生成风险明细、汇总和复核清单；提交与报告规则见 `references/submission-and-reporting.md`。

## 输出

新建结果工作簿/CSV 及摘要 JSON：`runId`、`store`、`checkedAt`、`sourceFileDigest`、`counts`、`rows[]`、`risks[]`、`unmatched[]`、`dataGaps[]`、`artifacts[]`。

## 写入与恢复

- 源文件永不覆盖；目标文件已存在时停止，除非用户明确授权替换，替换前创建备份。
- 定时执行仅在用户明确要求时按 `references/scheduling.md` 配置；普通核验后不主动创建。
- 线上价格读取只读；不改价、不领券、不下单、不提交活动。

## 验收

每行保留源行号、商品/SKU、两种价格、口径、时间戳和状态；汇总数量与明细一致；凭证与敏感字段未写入结果。
