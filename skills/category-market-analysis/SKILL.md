---
name: category-market-analysis
description: 基于已取得的类目榜单、价格带和卖点信号，计算品牌/店铺集中度、价格结构、卖点分布与 KANO 分层。适用于已有数据后的品类竞争格局分析；本 Skill 不负责远程取数。
---

# 品类市场竞争格局分析

本 Skill 是确定性分析节点。保留现有 `scripts/` 作为唯一计算入口，语义步骤只负责标题卖点归一与 KANO 终判，不能改写原始商品或排名字段。

## 输入

- `work_dir`：绝对路径，包含 `中间数据文件/top_items_raw.json`。
- `category_selling_point_strategy.json`：状态只能是 `ready`、`no_data` 或 `unavailable`。
- 可选价格档位、分析 Top N 与 KANO 配置。
- 上游推荐使用 `category-best-selling-items-analysis` 和 `category-price-band-analysis`；输入必须同类目、同周期、同店铺授权上下文。

## 主线

1. 按 `references/cross-platform-execution.md` 初始化，运行 `validate_input.py` 验签。失败立即停止。
2. 运行 `build_skeleton.py --stage attributes`，只填开放字段；`ready` 走权威卖点语义归一，降级态运行 `fill_attributes_fallback.py` 并保留 `_warnings`。
3. 运行 `verify_step.py --step Step3c`，通过后用 `analyze_market_share.py` 计算集中度、价格带与规则初判。
4. 运行 KANO 骨架与终判，禁止修改脚本锁定字段；执行 Step4b 校验。
5. 用 `extract_representative_items.py` 选取品牌/卖点/价格带代表商品，再执行 finalize 校验。
6. 用 `stamp_conclusion.py` 写入输入摘要、降级状态和验证凭证。

覆盖已有产物前必须使用脚本写入守卫和明确的 `--allow-overwrite`/`--restamp` 授权；脚本会创建恢复备份。

## 输出

- `{work_dir}/中间数据文件/market_share.json`
- `{work_dir}/中间数据文件/representative_items.json`
- 状态、输入摘要、验证凭证、降级警告与数据缺口。

字段契约见 `references/schemas.md`；卖点规则见 `references/selling-point-extraction.md`。

## 边界与验收

- 不自行取数，不从报告文本反推数据，不修改上游原始文件。
- 品牌、价格带、卖点份额的分母必须写明；区间与缺失值保持原语义。
- 任何 `<待填>`、身份不一致或验证失败都会阻止盖章。
- 仅在 `validation.valid=true` 且所有必需输入哈希存在时标记完成。
