> ⚠ 快照来源：skills/category-market-insight/references/schemas.md（拆分迁移，2026-08-21）。原件仍被迁移期单体使用；修改时评估双向同步。

# 中间数据 JSON Schema

> 本技能消费/产出的中间数据 JSON Schema 集中归档于此。SKILL.md 主流程图仅引用文件名，详细字段定义见本文档对应章节。上游取数产物（`price_segs.json` 字段口径）以 `category-top-items-fetch/references/field-dictionary.md` 为事实源。

---

## top_items_raw.json

由 Step 3 `fetch_top_items.py` 产出。

```json
{
  "cate_id": "50009211",
  "cate_flag": "0",
  "rank_type": "gmv",
  "date_type": "recent30",
  "fetched_at": "2026-05-23T10:00:00",
  "total_items": 400,
  "bands": [
    {
      "band": "0-135.0",
      "price_seg_id": "1",
      "items": [
        {
          "item_id": "1234567890",
          "title": "商品标题（已清洗）",
          "pict_url": "https://img.taobao.com/...",
          "detail_url": "https://item.taobao.com/item.htm?id=1234567890",
          "shop_title": "店铺名",
          "pay_byr_cnt_raw": "8万 ~ 12万",
          "pay_byr_cnt_min": 80000,
          "pay_byr_cnt_max": 120000,
          "uv": 1234567,
          "rank": 1,
          "rank_cycle_cqc": "..."
        }
      ]
    }
  ]
}
```

**关键字段**：

- `bands[i].price_seg_id`：本次实际使用的价格档位ID。值为 priceSegId 时表示走了 priceSeg 口径（数据池可拉满）；为 null 时表示回落到 minPrice/maxPrice 口径
- `pay_byr_cnt_min` / `pay_byr_cnt_max` / `pay_byr_cnt_raw`：三个独立字段，下游一律按 `pay_byr_cnt_min` 取数并标注「毛估」
- `total_items` = 各 band items 数之和（去重后），即下游 `analyze_market_share.py` 的占比分母

---

## category_selling_point_strategy.json

类目决策属性（类目决策词）依赖输入，由 `category-decision-factor-fetch` 产出、编排层透传（Schema 事实源 = 其 `references/output-contract.md`）。**必经文件**，但允许两条降级出口；⛔ 禁止手写 `source=placeholder` 占位文件。

### 正常返回 schema（status=ready）

主形态是 `consumer_decision_factors` 富结构（search / purchase 两个场景，每侧 `data.result[]` 含 pname/std_score_p/vname/std_score_v）；以下简化形态也兼容：

```json
{
  "category": "充电宝",
  "category_id": "50009211",
  "status": "ready",
  "source": "category-decision-factor-fetch",
  "fetched_at": "2026-05-23T19:30:00",
  "selling_point_strategy": [
    {"selling_point": "快充",       "weight_rank": 1, "is_core_factor": true,  "is_key_decision_attr": true},
    {"selling_point": "可上飞机",   "weight_rank": 5, "is_core_factor": true,  "is_key_decision_attr": true},
    {"selling_point": "多接口",     "weight_rank": 8, "is_core_factor": false, "is_key_decision_attr": true}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `weight_rank` | 越小越重要 |
| `is_core_factor` | true 时卖点提取必须优先匹配；脚本初判 D/P 阈值放宽 20%；模型终判（KANO 终判步）**不允许**判为无差异型 |
| `is_key_decision_attr` | 关键决策属性（用户在购买决策中关注度高） |

### 降级出口 1：status=no_data（权威空结果）

依赖可达、接口成功，但该类目确实没有决策属性。直接用依赖原产物，⛔ 禁止覆盖重写。

### 降级出口 2：status=unavailable（取数侧没取到决策属性）

取数技能 `category-top-items-fetch` 调依赖执行失败（超时/权限/参数/协议错误，或 output 未生成）时，由其 `scripts/strategy_handoff.py degrade` 直接写出空契约（首次失败即可降级；本技能只读不写，⛔ 禁止手写）：

```json
{
  "schemaVersion": 1,
  "mode": "category_decision_factors",
  "status": "unavailable",
  "degraded": true,
  "degradeReason": "dependency_failed",
  "requestId": "<与 request 文件一致>",
  "category_id": "50009211",
  "category_name": "充电宝",
  "category": "充电宝",
  "source": "category-decision-factor-fetch",
  "fetched_at": "2026-05-23T19:30:00",
  "unavailable_reason": "ATP timeout / HTTP 403 / JSON parse error 等真实原因",
  "attempts": 1,
  "consumer_decision_factors": {
    "search":   {"success": false, "data": {"result": []}, "error": "dependency_failed"},
    "purchase": {"success": false, "data": {"result": []}, "error": "dependency_failed"}
  },
  "stats": {"searchCount": 0, "purchaseCount": 0, "complete": false},
  "selling_point_strategy": [],
  "fallback": {"mode": "reference_keyword_table", "reference": "references/category-decision-attributes.md"}
}
```

硬约束：`degraded=true` + `degradeReason=dependency_failed` + `unavailable_reason` 非空 + `attempts >= 1`（真实尝试次数），四者缺一会被 `validate_input.py` / `verify_step.py --step Step3b` 拒收（避免无原因降级、避免手写占位冒充）。

> 两条降级出口下卖点提取才允许降级使用 [`category-decision-attributes.md`](category-decision-attributes.md) 关键词表作为主要依据，KANO 仅用脚本初判（无类目权威可放宽），并必须在 `item_attributes.json` 顶层 `_warnings` 记录降级原因（verify_step Step3c 强制校验）；降级信息由 `stamp_conclusion.py` 写入 `market_share.meta.inputs.strategy`，下游报告必须显式标注。

---

## item_attributes.json

由 Step 4 模型产出。

```json
{
  "extracted_at": "2026-05-22T10:00:00",
  "attribute_taxonomy_version": "v1",
  "authority_source": "category-decision-factor-fetch",
  "authority_count": 18,
  "_warnings": [
    "category-decision-factor-fetch 降级（status=unavailable，degradeReason=dependency_failed，原因=ATP timeout），本次卖点匹配走 references/category-decision-attributes.md 关键词表兜底"
  ],
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

| 字段 | 说明 |
|------|------|
| `authority_source` | 依赖返回的 source（正常为 `category-decision-factor-fetch`）；降级态仍写依赖名，降级事实靠 `_warnings` 与 strategy 文件的 status 识别 |
| `authority_count` | 依赖返回的权威属性条数；降级态（no_data / unavailable）为 `0` |
| `_warnings` | 降级态（status=no_data / unavailable）**必填**非空数组，记录 degradeReason 与真实原因；verify_step Step3c 强制校验 |
| `selling_point_origins[卖点]` | 取值 `authority`（类目权威词表命中）/ `reference_md`（参考 md 兜底命中）；用于事后审计「真正用了多少类目权威信号」 |
| `kano_layer` | 取值 `基础型 / 期望型 / 兴奋型 / 无差异型`；模型终判会在 Step 5.1 覆盖 |

**自检指标**：完成提取后统计 `selling_point_origins=authority` 的占比；若依赖返回非空（非降级态）但 authority 命中率 < 30%，需重新审视提取过程；降级态不做该校验。

---

## market_share.json

由 Step 5 `analyze_market_share.py` 产出，Step 5.1 通过 `--merge-kano-final` 回灌覆写。

```json
{
  "cate_name": "充电宝",
  "cate_id": "50009211",
  "rank_type": "gmv",
  "date_type": "recent30",
  "summary": {
    "total_items": 400,
    "total_pay_byr_cnt_min": 12345678,
    "top_n": 10
  },
  "category_authority_count": 18,
  "kano_profile": "default",
  "brand_share": [
    {
      "brand": "罗马仕",
      "item_count": 18,
      "item_share": 4.5,
      "pay_byr_cnt_min": 1234567,
      "pay_byr_cnt_share": 10.0,
      "head_item_ids": ["123", "456"]
    }
  ],
  "band_share": [
    {
      "band": "0-135.0",
      "item_count": 100,
      "item_share": 25.0,
      "pay_byr_cnt_min": 3456789,
      "pay_byr_cnt_share": 28.0,
      "top_concentration": 55.0
    }
  ],
  "selling_point_share": [
    {
      "selling_point": "快充",
      "is_core_factor": true,
      "item_count": 120,
      "item_share": 30.0,
      "pay_byr_cnt_min": 4567890,
      "pay_byr_cnt_share": 37.0,
      "top_concentration": 40.0,
      "metrics": {
        "D_buyer_share": 0.30,
        "P_item_coverage": 0.37,
        "R_premium": 1.23,
        "H_head_support": 0.40,
        "E_price_premium": 0.07
      },
      "kano_initial_suggestion": "期望型",
      "kano_rule_hit": "R3",
      "rule_match_detail": "D >= 0.25 且 P >= 0.30 且 R > 1.0",
      "kano_final": {
        "kano_layer": "期望型",
        "agree_with_rule": true,
        "override_reason": null,
        "confidence": 0.92,
        "evidence_summary": "..."
      },
      "kano_layer": "期望型",
      "kano_decision_source": "model_final"
    }
  ],
  "kano_final_missed": []
}
```

**关键字段**：

| 字段 | 说明 |
|------|------|
| `summary.total_items` | 实际抓取总样本量（即占比分母），**禁止写死为 100** |
| `summary.total_pay_byr_cnt_min` | 全样本 `pay_byr_cnt_min` 累加（毛估） |
| `category_authority_count` | Step 4.0 返回的权威卖点条数；占位场景为 0 |
| `kano_profile` | Step 2.3 前置选定的 profile（`default` / `custom`） |
| `band_share` | 价格带维度占比（注意 key 是 `band_share` 不是 `price_band_share`） |
| `item_share` | 百分比（0-100），不是小数比例 |
| `pay_byr_cnt_share` | 百分比（0-100），不是小数比例 |
| `top_concentration` | 头部集中度百分比（仅 band_share 和 selling_point_share 有此字段，brand_share 无） |
| `metrics.D_buyer_share` / `P_item_coverage` / `R_premium` / `H_head_support` / `E_price_premium` | 电商版 KANO 量化指标，嵌套在 `metrics` 内（详见 `category-decision-attributes.md` 第六章） |
| `kano_initial_suggestion` | 脚本初判结果 |
| `kano_rule_hit` | 命中的初判规则编号（R0~R4） |
| `kano_final` | **必须是 dict**（详见下方硬要求） |
| `kano_layer` / `kano_decision_source` | 回灌后由脚本同步覆写 |
| `kano_final_missed` | 模型未在 kano_final.json 中提及的卖点列表，供下游审计 |

⛔ **`kano_final` schema 硬要求**：必须是 **dict**，**禁止字符串**——`generate_excel_report.py._kano_final` 用 `.get("kano_layer")` 读取，写成字符串会直接报 `'str' object has no attribute 'get'`。Step 7.0 / `preflight_check.py` 会强制校验此项。

---

## kano_final.json

由 Step 5.1 模型产出。

```json
{
  "version": "v1",
  "selling_points": [
    {
      "selling_point": "可上飞机",
      "kano_initial": "无差异型",
      "kano_final": {
        "kano_layer": "期望型",
        "agree_with_rule": false,
        "override_reason": "类目权威 is_core_factor=true；样本内 P=0.55，R=1.17，仅因 D 近阈值被 R0 占位；语义上为出行场景刚需",
        "confidence": 0.82,
        "evidence_summary": "该卖点仅 12% 覆盖但贡献 18% 买家，且集中在 220元+ 价格带"
      }
    }
  ]
}
```

**强制规则**（与 SKILL.md Step 5.1 一致）：

1. `kano_final.kano_layer` 取值：`基础型 / 期望型 / 兴奋型 / 无差异型`，不允许「未命中」
2. `kano_final` 必须是 **dict**，禁止字符串
3. 终判覆盖初判（`agree_with_rule=false`）必须填非空且含具体证据的 `override_reason`（量化指标 + 权威信号 + 语义）
4. `confidence` ∈ [0,1]
5. 凡 `is_core_factor=true` 的卖点：初判为 R0 / R4 时默认覆盖为期望型或基础型
6. 不能修改脚本产出的 D/P/R/H/E 原始指标

> 本品（own_product）模式的 `own_product.json` / `own_positioning.json` 不由本技能读写，Schema 见迁移期单体技能 `skills/category-market-insight/references/schemas.md`。
