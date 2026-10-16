# 定时核价

仅当用户主动提出定时、每天或自动核价时使用本流程。普通单次核价结束后不要主动询问或推销定时任务。

## 确认配置

通过弹窗展示并确认：

- 价盘文件名和本地路径。
- 核价口径。
- 查询日期固定取每次触发当天。
- 风险判定规则。
- 执行时间固定为每天 08:00 和 18:00。

用户取消时直接结束，不创建任务。

## 创建任务

用户确认后调用运行时提供的 `create_cron_task`：

| 参数 | 值 |
|---|---|
| `name` | `每日核价_{fileName}_{口径中文名}` |
| `cron` | `0 0 8,18 * * ?` |
| `input` | 下方完整指令 |

```text
执行定时核价任务。参数如下：
- 价盘文件本地路径：{localFilePath}
- 文件名：{fileName}
- 核价口径（scene）：{scene}
- 风险判定规则：thresholdType={NUMBER|PERCENT}，highThreshold={value}，lowThreshold={value}
- Sheet：{sheetName}
- 表头行：{headerRow}
- 字段映射：itemId={itemIdSelector}，skuId={skuIdSelector}，priceMode={single|item_sku}，price={priceSelectorOrEmpty}，itemPrice={itemPriceSelectorOrEmpty}，skuPrice={skuPriceSelectorOrEmpty}，cost={costSelectorOrEmpty}
- 查询时间：取任务触发当天日期，格式 yyyy-MM-dd
```

创建成功后告知用户每天执行时间和任务中心管理入口。创建失败时展示真实原因，不自动重复创建。

## 定时触发逻辑

触发后不要弹窗或询问：

1. 使用记录的文件路径、Sheet 和表头行重新 analyze。
2. 仅当 Sheet、表头和全部 selector 仍有效时 clean；结构变化时推送失败原因，禁止重新猜测。
3. 使用当天日期调用统一 CLI 的 batch-check 子命令（`--apply-time` 取触发当天 `yyyy-MM-dd`，`--scene` / `--threshold-type` / `--low` / `--high` 沿用记录参数），逐行读取 stdout 的 parsed / batch / done 进度事件。
4. 收到 `done` 事件后，按 `summary` 推送风险汇总，并用 `present_files(files=[{"file_path": summary.output_path}])` 将结果文件以文件卡片形式展示；`aborted=true` 时在推送中说明因失败率过高提前终止。
5. 不展示定时任务后续操作按钮。

本地文件被移动、删除或不可访问时，推送“定时核价失败：价盘文件不可访问，请重新手动执行核价并重新设置定时任务”，不重试、不自动取消现有任务。
