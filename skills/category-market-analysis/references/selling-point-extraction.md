> ⚠ 快照来源：skills/category-market-insight/references/selling-point-extraction.md（拆分迁移，2026-08-21）。原件仍被迁移期单体使用；修改时评估双向同步。

# 卖点提取工作指引

> **作用**：指导模型在 Step 4 中如何从商品标题提取「品牌 + 卖点 + 价格信号 + KANO 层」。
> **配套词典优先级（强约束）**：
>
> 1. **首选**：`中间数据文件/category_selling_point_strategy.json` —— 上游取数技能产出的富结构卖点（来自类目搜索/加购/评论决策属性），权威性最高。
>    - 卖点关键词来自 `consumer_decision_factors.{search,purchase}.data.result[].v_list[].vname`（**vname 才是卖点词**，pname 是属性名不要进卖点）
>    - ⛔ `pname` 为「品牌/品牌名/品牌类型/brand」的属性块，其 `v_list[].vname`（具体品牌名）**不进卖点词表**，品牌由独立的品牌识别逻辑处理（见下方§品牌识别）；`analyze_market_share.py` 已在代码层面过滤。注意「适配机型/适配品牌/兼容品牌」等 pname 不在此列，其 vname 仍作为合法卖点保留
>    - 也包含 `selling_point_recommendations.core_selling_points[].name`（核心卖点） / `summary.top_decision_attributes[].top_values` 等冗余信号
>    - `analyze_market_share.py` 的 `load_strategy_authority` 已把这些字段统一规整为 `权威词表`（含 `is_core_factor` / `weight_rank`），下游脚本和模型 Prompt 都应直接消费
> 2. **兜底**：[`category-decision-attributes.md`](category-decision-attributes.md) 通用关键词表（在没有类目权威数据，或权威词表未覆盖时使用）
>
> **降级态（strategy `status=no_data` 或 `status=unavailable`）**：权威词表为空，全部卖点走兜底词表，`selling_point_origins` 全为 `reference_md`；KANO 仅用脚本初判（无类目权威可放宽）；`item_attributes.json` 顶层 `_warnings` 必须非空并记录降级原因（verify_step Step3c 强制）；不做 authority 命中率 ≥30% 校验。
> ⚡ 降级态不由模型逐条提取：跑 `scripts/fill_attributes_fallback.py`（关键词表确定性归一，下方「逐商品提取步骤」已全部实现）；模型只补脚本 stdout 报告的未命中商品（`itemsWithoutSellingPoint`），本文下文此时作为补填时的归一口径参考。
>
> 模型在标题提取时按 `权威词表 → 通用词表` 优先级匹配；命中权威词必须保留，命中通用词时若与权威词冲突以权威为准。

## 工作流

### 1. 输入

- `top_items_raw.json` 中的 items 列表（每个商品含 `itemId`, `title`, `band`, `shopTitle` 等）
- `中间数据文件/category_selling_point_strategy.json`（权威富结构 v2，五大块：consumer_decision_factors / image_selling_point_factors / image_position_strategy / selling_point_recommendations / summary）

### 2. 逐商品提取步骤

对每条商品，按下述顺序执行：

1. **品牌识别** → 写入 `brand`
   - **优先从 `shopTitle` 提取品牌**（如「图拉斯旗舰店」→「图拉斯」）
   - 标题中的适配/兼容品牌禁止误判（如「适用于华为/苹果手机壳」中的「华为/苹果」不是产品品牌）
   - 英文品牌归一为中文写法（参考 attributes 表）
   - 店铺名和标题均无法识别时填 `null`
2. **卖点识别** → 写入 `selling_points`（数组）+ `selling_point_categories`（按 8 大类分组）
   - **第一遍**：以富结构 `v_list[].vname` + `core_selling_points[].name` 拼成的「权威词表」匹配标题，命中即归一为该 vname/name 主词
   - **第二遍**：剩余位置再用 `category-decision-attributes.md` 通用词典补足（仅作兜底）
   - 命中同义词时，归一为「主词」
   - 一个商品最多保留 6 个最显著的卖点（标题前置 + 出现频次靠前优先）
   - **禁止**把 pname（属性名，如「功能」「款式」）当作卖点；只能取 vname（属性值，如「双向快充」「便携式」）
3. **价格信号** → 写入 `price_signal`
   - 仅捕捉标题中的价格态度词（亲民/高端/折扣/满减），不进 `selling_points`
4. **KANO 层** → 写入 `kano_layer`
   - 取该商品最显著卖点对应的 KANO 默认层（参见 attributes 表第二节）
   - 若卖点全部为价格信号或为空，记为 `无差异型`

### 3. 输出

写入 `中间数据文件/item_attributes.json`，格式：

```json
{
  "extracted_at": "2026-05-22T10:00:00",
  "attribute_taxonomy_version": "v1",
  "authority_source": "category-decision-factor-fetch",
  "authority_count": 18,
  "_warnings": ["降级态（status=no_data / unavailable）必填，记录 degradeReason 与真实原因"],
  "items": [
    {
      "itemId": "1234567890",
      "band": "50-200",
      "brand": "兰蔻",
      "selling_points": ["保湿", "敏感肌", "玻尿酸"],
      "selling_point_categories": {
        "功效": ["保湿"],
        "人群": ["敏感肌"],
        "成分": ["玻尿酸"]
      },
      "selling_point_origins": {
        "保湿": "authority",
        "敏感肌": "authority",
        "玻尿酸": "reference_md"
      },
      "kano_layer": "期望型",
      "price_signal": null
    }
  ]
}
```

**必填字段说明**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `authority_source` | ✅ | 依赖返回的 source 值（正常为 `category-decision-factor-fetch`）；⛔ 禁写 `"placeholder"` |
| `authority_count` | ✅ | 依赖返回的权威属性条数；降级态（no_data / unavailable）为 `0` |
| `_warnings` | 条件 | strategy 处于降级态（`status=no_data` / `status=unavailable` / `degraded=true`）时**必填非空数组**，记录降级原因（build_skeleton.py 已预填一条，模型不得删除）|
| `selling_point_origins` | ✅ | **每个 selling_points 中的卖点必须在此有对应键**；取值仅 `authority`（类目权威词表命中）或 `reference_md`（通用词典兜底），禁止 `null/manual/auto` |
```

## Few-shot 示例

### 示例 1：美妆个护

**标题**：`兰蔻菁纯臻颜眼霜玻尿酸抗皱紧致黑眼圈眼袋熊猫眼眼霜礼盒装`

**输出**：
```json
{
  "brand": "兰蔻",
  "selling_points": ["抗衰", "玻尿酸", "礼盒装"],
  "selling_point_categories": {
    "功效": ["抗衰"],
    "成分": ["玻尿酸"],
    "赠品": ["礼盒装"]
  },
  "kano_layer": "期望型",
  "price_signal": null
}
```

> 「抗皱紧致」归一为「抗衰」；「黑眼圈眼袋熊猫眼」未在词典中保留为长尾，不强行加入。

### 示例 2：服饰鞋包

**标题**：`UNIQLO优衣库女士莫代尔棉质短袖T恤夏季通勤简约百搭白色 XL`

**输出**：
```json
{
  "brand": "优衣库",
  "selling_points": ["纯棉", "通勤", "女士"],
  "selling_point_categories": {
    "成分": ["纯棉"],
    "场景": ["通勤"],
    "人群": ["女士"]
  },
  "kano_layer": "期望型",
  "price_signal": null
}
```

> UNIQLO 归一为「优衣库」；「莫代尔棉质」中的「棉质」归一为「纯棉」。

### 示例 3：食品生鲜

**标题**：`三只松鼠每日坚果混合坚果750g礼盒装年货送礼食品级 央视上榜`

**输出**：
```json
{
  "brand": "三只松鼠",
  "selling_points": ["礼盒装", "节庆", "食品级", "央视"],
  "selling_point_categories": {
    "赠品": ["礼盒装"],
    "场景": ["节庆"],
    "资质": ["食品级", "央视"]
  },
  "kano_layer": "兴奋型",
  "price_signal": null
}
```

> 「年货送礼」归一为「节庆」；同一商品命中多个资质词时全部保留。

### 示例 4：3C 数码

**标题**：`华为Mate60 Pro 5G手机黑科技专利国产高端旗舰 顺丰包邮 12+512`

**输出**：
```json
{
  "brand": "华为",
  "selling_points": ["黑科技", "专利", "国货", "顺丰包邮"],
  "selling_point_categories": {
    "工艺": ["黑科技", "专利"],
    "资质": ["国货"],
    "赠品": ["顺丰包邮"]
  },
  "kano_layer": "兴奋型",
  "price_signal": "高端"
}
```

> 「高端旗舰」识别为价格信号，写入 `price_signal`；不进 `selling_points`。此例 `shopTitle`=「华为官方旗舰店」，店铺名确认品牌为「华为」。

### 示例 4b：3C 数码配件（适配品牌 ≠ 产品品牌）

**标题**：`适用于华为 Mate60/苹果 iPhone15 手机壳透明防摔硬壳磁吸保护套`
**shopTitle**：`图拉斯旗舰店`

**输出**：
```json
{
  "brand": "图拉斯",
  "selling_points": ["透明", "防摔", "磁吸"],
  "selling_point_categories": {
    "功效": ["防摔"],
    "工艺": ["透明", "磁吸"]
  },
  "kano_layer": "期望型",
  "price_signal": null
}
```

> ❗ 标题中的「华为」「苹果」是适配对象，不是产品品牌。品牌从 `shopTitle`「图拉斯旗舰店」提取为「图拉斯」。

### 示例 5：家居家装（无品牌）

**标题**：`实木餐桌椅组合家用现代简约小户型北欧饭桌4人6人吃饭桌子`

**输出**：
```json
{
  "brand": null,
  "selling_points": ["实木", "居家"],
  "selling_point_categories": {
    "成分": ["实木"],
    "场景": ["居家"]
  },
  "kano_layer": "期望型",
  "price_signal": null
}
```

> 标题无品牌信息且店铺名也无法识别时 `brand` 填 `null`，不写「白牌」。

### 示例 6：母婴

**标题**：`Babycare婴儿纸尿裤皇室狮子王国NB码新生儿超薄透气干爽 试用装`

**输出**：
```json
{
  "brand": "Babycare",
  "selling_points": ["婴幼儿", "透气", "试用装"],
  "selling_point_categories": {
    "人群": ["婴幼儿"],
    "功效": ["透气"],
    "赠品": ["试用装"]
  },
  "kano_layer": "期望型",
  "price_signal": null
}
```

### 示例 7：运动户外

**标题**：`迪卡侬户外露营帐篷防水防晒3-4人速开自动便携野营 终身保修`

**输出**：
```json
{
  "brand": "迪卡侬",
  "selling_points": ["户外", "防水", "防晒", "旅行", "终身保修"],
  "selling_point_categories": {
    "场景": ["户外", "旅行"],
    "功效": ["防水", "防晒"],
    "赠品": ["终身保修"]
  },
  "kano_layer": "兴奋型",
  "price_signal": null
}
```

> 「便携」归一为「旅行」；超过 6 个卖点时只保留最显著的前 6 个。

### 示例 8：低质量标题

**标题**：`厂家直销特价限时5折包邮`

**输出**：
```json
{
  "brand": null,
  "selling_points": ["顺丰包邮"],
  "selling_point_categories": {
    "赠品": ["顺丰包邮"]
  },
  "kano_layer": "无差异型",
  "price_signal": "折扣"
}
```

> 卖点几乎全为价格信号时，`kano_layer` 记为「无差异型」，提示该商品依赖价格驱动。

## 校验规则

提取完成后，模型必须自检以下 4 条：

1. ✅ 每个 itemId 都对应一条记录
2. ✅ 所有 `selling_points` 中的词都来自 attributes 表的「主词」列（不是同义词）
3. ✅ `selling_point_categories` 与 `selling_points` 一致（无遗漏、无多余）
4. ✅ `kano_layer` 取值在 `{基础型, 期望型, 兴奋型, 无差异型}` 范围内

任何一条校验失败需修正后再写入文件。
