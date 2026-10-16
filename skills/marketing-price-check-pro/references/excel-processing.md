# Excel 分析与清洗

## 目录

- [分析字段结构](#分析字段结构)
- [选择-sheet-与确认表头](#选择-sheet-与确认表头)
- [确认字段映射](#确认字段映射)
- [执行清洗](#执行清洗)
- [错误处理](#错误处理)

`{P}` 表示 Skill 内的 `scripts/price_check.py`。macOS 和 Windows 使用相同命令与参数；脚本只使用 Python 3.11 标准库，禁止安装或调用 `openpyxl`、`pandas` 等第三方包。

## 分析字段结构

```text
python -X utf8 "{P}" analyze "{localFilePath}"
```

解析 JSON：

- `sheets`：仅包含可见业务 Sheet 的状态、表头、行列、重复列诊断和隐藏字典信息；隐藏、veryHidden 和 `_hide` 技术 Sheet 不得出现在该数组中。
- `visible_sheets`：可供选择的可见业务 Sheet。
- `selected_sheet`：仅有一个可见 Sheet 时自动选择，否则为 null。
- `header_row`：前 50 个 Excel 物理行中探测到的表头行。
- `column_options`：稳定列选择器、展示名和隐藏机器字段。
- `identified`：商品 ID、SKU ID、成本价、价格候选和价格模式的自动识别结果。

后续字段映射必须保存 `column_options.selector`，例如 `col:A`；展示时使用 `label`。

## 选择 Sheet 与确认表头

多个可见 Sheet 时，只能使用 `sheets` 或 `visible_sheets` 生成候选项，并使用 `sheets` 中的列数和 `row_count` 补充说明。不得从其他字段、工作簿原始结构或隐藏字段字典补充候选项。用户选择后重新分析：

```text
python -X utf8 "{P}" analyze "{localFilePath}" --sheet "{sheetName}"
```

禁止展示、选择或清洗隐藏、veryHidden 或 `_hide` 技术 Sheet。

所有文件都展示探测到的表头行和列，并让用户确认。用户调整时只接受 1～50 的正整数，然后重新分析：

```text
python -X utf8 "{P}" analyze "{localFilePath}" --sheet "{sheetName}" --header-row {headerRow}
```

重新分析后必须使用新返回的 `column_options` 和 `identified`，禁止沿用旧映射。

## 确认字段映射

价格层级默认自动判定，不需要询问用户「单价格还是双层价格」：优先使用 SKU 层级价格，某行没有 SKU 时直接回退使用商品层级价格。

当 `price_mode=item_sku` 且 `item_price`、`sku_price` 均非空时，按下述规则自动取价并展示确认所用列（不再询问价格模式选择）：

- 商品 ID 字段。
- SKU ID 字段。
- 商品价格字段。
- SKU 价格字段。
- 取价规则（自动生效）：有 SKU ID 的行取 SKU 价格，无 SKU ID 的行取商品价格。
- 成本价字段或“未检测到”。

当 `price_mode=single` 时，展示商品 ID、SKU ID、价格候选和可选成本价。只有一个价格候选时直接使用；多个候选时让用户选择一个。

识别失败或用户手动调整时，所有选项必须来自 `column_options.label`，内部保存对应 selector。需确认的项：

1. 商品 ID 字段。
2. SKU ID 字段。
3. 对应价格字段（价格层级优先级自动按 SKU 优先、无 SKU 回退商品，不作为选项询问）。
4. 可选成本价字段。

## 执行清洗

输出目录必须是主 Agent 可访问的工作目录。

单价格模式：

```text
python -X utf8 "{P}" clean "{localFilePath}" --sheet "{sheetName}" --header-row {headerRow} --item-id "{itemIdSelector}" --sku-id "{skuIdSelector}" --price "{priceSelector}" --cost "{costSelector}" --outdir "{outputDir}"
```

成本价未选择时省略 `--cost`。双层价格模式用以下两个参数替换 `--price`：

```text
--item-price "{itemPriceSelector}" --sku-price "{skuPriceSelector}"
```

清洗文件固定输出“商品ID、SKU ID、成本价、本地核验价”。ID 按文本写出；成本价未选时留空；跳过全空行。

记录脚本返回的 `output_path`、`output_name`、`row_count`、`header_row`、`price_mode`、`item_row_count`、`sku_row_count` 和 `companion_sheet`。

## 错误处理

以下情况立即展示脚本错误并终止当前执行：

- Sheet 不存在或属于隐藏技术 Sheet。
- 表头不存在、为空或不在指定物理行。
- 重复展示名无法由唯一机器字段消歧。
- 隐藏机器字段重复。
- selector 不存在或多个角色映射到同一列。
- 双层价格模式下，SKU ID 与 SKU 价格存在性不一致。
- 无 SKU 行缺少商品价格。
- `python` 命令不存在、版本低于 3.11，或脚本返回 `Traceback` / `ImportError`。

禁止回退到第一张 Sheet、旧表头、旧字段映射或猜测的新列。
