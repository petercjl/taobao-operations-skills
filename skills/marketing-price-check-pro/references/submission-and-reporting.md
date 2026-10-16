# 批量同步核价与生成报告

## 目录

- [调用批量核价](#调用批量核价)
- [进度事件契约](#进度事件契约)
- [单批状态含义](#单批状态含义)
- [失败与熔断处理](#失败与熔断处理)
- [完成事件与报告字段](#完成事件与报告字段)
- [风险汇总展示](#风险汇总展示)
- [展示结果文件](#展示结果文件)
- [重试边界](#重试边界)

`{P}` 表示 Skill 内的 `scripts/price_check.py`。所有阶段都使用同一 Python CLI，不选择操作系统或平台脚本。

## 调用批量核价

清洗完成后，直接对清洗产物调用 `batch-check` 子命令，无需上传 OSS、无需异步提交、无需等待推送：

```text
python -X utf8 "{P}" batch-check "{cleanOutputPath}" --apply-time "{yyyy-MM-dd}" --scene "{scene}" --threshold-type "{NUMBER|PERCENT}" --low "{positiveNumber}" --high "{positiveNumber}" --outdir "{outputDir}"
```

- `{cleanOutputPath}`：clean 子命令产出的固定四列清洗文件（商品ID / SKU ID / 成本价 / 本地核验价）。
- `--apply-time`：查询日期，格式必须为 `yyyy-MM-dd`（当天或未来 15 天内），不支持时分秒。
- `--scene`：价格口径，取值 `bid_price` / `predict_pmp` / `risk_argus_predict_p` / `risk_health_upgrade`。
- `--threshold-type`：`NUMBER`（按差值）或 `PERCENT`（按百分比）。
- `--low` / `--high`：风险阈值绝对值，均须为正数。
- `--outdir`：结果 xlsx 输出目录，缺省为当前目录。
- 可选 `--batch-size`（默认 10）和 `--sleep`（默认 0.3 秒）用于调节分批粒度与基础限流间隔，一般无需指定。

`batch-check` 内部读取清洗文件、按批（默认每批 10 条）串行调用运行时内置的 `atp` 核价工具（健康中心核价，`tool_78717bjpsy` v0.0.2），sellerId 与会话上下文由运行时自动注入。每批调用之间按限流节奏 sleep，禁止并发拉起多个批次。全部批次处理完后在 `{outputDir}` 落盘结果 xlsx，并回读校验表头与数据行数，再用 `report()` 统计风险。

## 进度事件契约

`batch-check` 把进度以 JSON Lines（每行一个 JSON 对象）写入 stdout，必须逐行解析，不要只取最后一行。三类事件：

| event | 时机 | 关键字段 |
|---|---|---|
| `parsed` | 清洗文件解析完成 | `total`（全部记录数）、`valid`（满足必填字段的记录数） |
| `batch` | 每处理完一批 | `batchIndex`、`totalBatches`、`written`、`ok`、`fail`、`skipped`、`status` |
| `done` | 全部完成、结果已落盘并统计 | `summary`（风险汇总对象，见下文） |

收到 `parsed` 后可向用户说明共多少商品、多少有效；收到每个 `batch` 事件可实时汇报进度（如“第 3/12 批完成，成功 28 / 失败 0 / 跳过 2”）；收到 `done` 后按 `summary` 生成最终风险汇总。

不可恢复错误不会走 `done`，而是以 `{"error":"..."}` 写入 stderr 并以退出码 1 结束；此时展示错误原文并终止，禁止臆造风险结论。

## 单批状态含义

`batch` 事件的 `status` 字段：

| status | 含义 | 处理 |
|---|---|---|
| `success` | 该批调用成功并解析到商品响应 | 正常累计 ok |
| `all_invalid` | 该批全部记录必填字段缺失，未发起调用 | 计入 skipped，不算失败 |
| `cli_error` | atp 命令返回非零 | 该批记录计入 fail，累计连续失败 |
| `biz_fail` | 接口返回 success=false（如额度不足） | 该批记录计入 fail，备注写入 errorMessage |
| `aborted` | 因失败率过高提前终止后剩余批次 | 记录写占位备注“因批量失败率过高，已提前终止” |

有效记录未在响应中回配时计入 fail，备注写入该批错误说明或“接口未返回该商品”；必填字段缺失的记录计入 skipped，备注固定为“必填字段缺失”。这些非空备注会在报告阶段进入 `excluded_count`，不参与正常/过低/过高统计。

## 失败与熔断处理

`batch-check` 内置节流与熔断，无需上层干预：

- 限流：批间基础 sleep 0.3 秒；连续 2 批失败时提升到至少 1.5 秒；连续 2 批成功后恢复基础间隔。
- 熔断：已处理批次数 ≥ 3 且失败批占比 > 50% 时，提前终止剩余批次，剩余记录写占位备注，`done.summary.aborted=true`。
- 触发熔断时仍会落盘并统计已完成部分；向用户说明“因失败率过高提前终止，仅前 N 批为有效结果”，建议检查商家登录态或稍后重跑完整核价。

## 完成事件与报告字段

`done.summary` 由 `report()` 统计后追加执行元信息，字段如下：

- `total`：全部非空商品记录数。
- `evaluated_count`：实际参与风险判定的记录数（备注为空者）。
- `excluded_count` / `excluded_pct`：因备注非空排除的记录数及其占 `total` 比例。
- `normal_count` / `normal_pct`、`low_count` / `low_pct`、`high_count` / `high_pct`：以 `evaluated_count` 为分母。
- `detail_limit`：每类明细最多返回条数。
- `low_items` / `high_items` / `excluded_items` 及各自的 `*_items_returned`、`*_items_truncated`。
- `output_path` / `output_name`：结果 xlsx 绝对路径与文件名。
- `applyTime` / `scene` / `scene_label`：本次查询日期、口径代码与中文口径名。
- `ok` / `fail` / `skipped`：成功、失败、跳过的记录数（执行口径，与风险口径分开）。
- `aborted`：是否因熔断提前终止。

风险百分比只以 `evaluated_count` 为分母；备注非空的记录优先归入排除项。

## 风险汇总展示

```text
📊 核价完成 - 风险汇总

共处理：{total} 个商品
参与风险判定：{evaluated_count} 个
因备注异常排除：{excluded_count} 个 ({excluded_pct}%)

风险分布（以参与风险判定商品为分母）：
✅ 正常：{normal_count} 个 ({normal_pct}%)
❗️ 价格过低：{low_count} 个 ({low_pct}%)
💡 价格过高：{high_count} 个 ({high_pct}%)
```

分别展示 `low_items` 和 `high_items`。价格展示两位小数，差价率展示脚本返回值，缺失字段和优惠组合缺失展示“—”。当 `low_items_truncated` 或 `high_items_truncated` 为 true 时，明确告知只展示前 `detail_limit` 条，完整列表以结果 xlsx 为准。`aborted=true` 时额外提示本次因失败率过高提前终止。

## 展示结果文件

风险汇总完成后，使用 `present_files` 工具将结果文件以文件卡片形式直接展示给用户：

```text
present_files(files=[{"file_path": "{output_path}"}])
```

- `{output_path}` 直接使用 `done.summary.output_path` 的值，不做路径转换（不改反斜杠为正斜杠，不添加本地文件 URI 前缀，不复制或移动文件）。
- 只调用一次。展示成功后，文件会以可点击的卡片形式出现在对话中，用户可直接下载或打开；无需在回复文本中额外输出文件路径或 `[SANDBOX_ARTIFACT:...]` 标记。
- 禁止使用 `local_declare_artifact`、反引号路径、`[文件名](本地路径)` 等文本格式代替文件卡片展示。
- 调用失败时，向用户展示原始 `output_path` 和失败原因后结束；禁止变换路径反复调用。

普通单次核价在此结束，不主动询问定时任务。

## 重试边界

- `batch-check` 是单进程同步命令：内部已对每批做限流与熔断，进程整体只在因传输类原因整体失败（如运行时环境瞬时不可用）时，才允许原样重跑同一命令、相同参数，包含首次调用在内最多 3 次。
- 每次自动重试都必须使用同一子命令和相同参数，不改口径、不改阈值、不改价盘。
- 参数错误、清洗文件结构错误、表头校验失败、结果回读校验失败、`atp` 运行时缺失或 Python 运行时错误均不得自动重试。
- 熔断（`aborted=true`）属于业务结果而非传输故障，不自动整体重试；应向用户说明并由其确认后重新发起完整核价。
- 用户修正价盘或参数并确认后，可开始一轮新的完整执行。
