# 执行流程与决策树

本文件定义 `sycm-item-rank-helper` 技能的完整执行流程，包括意图识别、参数提取、缺失检测、参数收集和 sycm-agent 传递规范。

---

## 执行步骤总览

```
Step 1: 意图识别 → 确定用户想用哪个（些）工具
Step 2: 参数提取 → 从用户语句中提取已有参数
Step 3: 缺失检测 → 对照必填参数清单，识别缺失项
Step 4: 参数收集 → 使用 ask_user_question 批量提问补全缺失参数
Step 5: 组装并传递 → 将用户原始请求 + 已确认参数组装为完整 prompt，调用 sycm-agent
```

---

## Step 1: 意图识别

### 意图分类决策树

```
用户请求
├─ 提到"商品排行/排名/卖得最好/销量Top"等列表类需求？
│   ├─ 提到"推广/直通车/万相台/引力魔方"？
│   │   └─ → dmp-items（推广商品排行）
│   ├─ 提到"我关注/收藏的商品"？
│   │   ├─ 提到"整体/汇总/含渠道品/总成交"？
│   │   │   └─ → my-items-whole
│   │   └─ 否则 → my-items（拆分视角，默认）
│   └─ 否则（全部商品）
│       ├─ 提到"整体/汇总/含渠道品/总成交"？
│       │   └─ → all-items-whole
│       └─ 否则 → all-items（拆分视角，默认）
│
├─ 提到具体商品 ID 或"某个商品的..."？
│   ├─ "核心指标/概览/整体表现" → item-overview
│   ├─ "趋势/走势/变化" → item-trend（需确认 indexCode）
│   ├─ "流量来源/流量从哪来/渠道" → item-flow
│   ├─ "SKU/规格/哪个颜色卖得好" → item-sku
│   ├─ "搜索词/关键词/搜什么词" → item-searchword
│   └─ "运营动作/短视频带货/新客引导/营销活动" → item-action
│
└─ 意图不明确（如"帮我看看商品数据"）
    └─ → 需通过 ask_user_question 确认分析类型
```

### 意图不明确时的提问模板

当无法从用户语句中确定具体工具时，提问：

```
问题：您想查看哪类商品数据？
选项：
1. 商品排行榜（推荐）— 查看全店商品的销售排名，支持按支付金额、销量、访客数等排序
2. 推广商品排行 — 查看直通车/万相台等推广商品的花费、ROI、展现等数据
3. 我关注的商品 — 查看已关注商品的表现
4. 单品深度分析 — 对某个具体商品查看流量来源、SKU、搜索词、趋势等
```

---

## Step 2: 参数提取

### 从用户自然语言中提取参数

| 参数 | 提取规则 | 示例 |
|------|---------|------|
| dateType | "昨天"→day、"近7天/最近一周"→recent7、"近30天/最近一个月"→recent30、"上周"→week、"上个月"→month | — |
| dateRange | 根据 dateType 计算（见 KNOWLEDGE.md 日期计算规则） | day+昨天 → "2026-06-21|2026-06-21" |
| itemId | 用户语句中出现的纯数字 ID（通常 10-15 位） | "商品 675099575218" → 675099575218 |
| 视角 | "整体/汇总/含渠道品/总成交"→整体；否则→拆分（默认） | — |
| device | "PC端/电脑端"→1、"无线端/手机端/移动端"→2；否则→0（默认） | — |
| orderBy | "按销售额"→payAmt、"按销量"→payItmCnt/payOrdItemQty、"按访客"→itmUv、"按转化率"→payRate | — |
| compareType | "较上一周期/环比"→cycle、"较日常平均"→dailyAvg、"较同类商品"→cmptItem | — |
| keyword | 用户提到的商品名称关键词 | "连衣裙" → keyword=连衣裙 |
| pageSize | "Top5"→5、"Top10"→10、"Top20"→20；默认 10 | — |
| indexCode | item-trend 必填，从用户指定指标提取 | "看支付金额趋势"→payAmt |

### 提取注意事项

- 用户说"今天"→ 提示离线口径 T-1，建议改查"昨天"
- 用户说"最近"但未指定天数 → 默认推荐"近 7 天"
- 用户说"上周"但未明确具体日期 → 需确认是自然周还是最近 7 天
- 用户提到多个商品 ID → 全部提取，后续可批量下钻
- 用户提到"Top N" → 提取 N 作为 pageSize

---

## Step 3: 缺失检测

### 各工具必填参数清单

| 工具 | 必填参数 | 常见缺失场景 |
|------|---------|-------------|
| all-items / all-items-whole | dateType, dateRange | 用户未指定时间 |
| my-items / my-items-whole | dateType, dateRange | 用户未指定时间 |
| dmp-items | dateType, dateRange | 用户未指定时间 |
| item-overview | itemId, dateType, dateRange | 用户未给商品 ID 或时间 |
| item-trend | itemId, dateType, dateRange, indexCode | 用户未给商品 ID / 时间 / 指标 |
| item-flow | itemId, dateType, dateRange | 用户未给商品 ID 或时间 |
| item-sku | itemId, dateType, dateRange | 用户未给商品 ID 或时间 |
| item-searchword | itemId, dateType, dateRange | 用户未给商品 ID 或时间 |
| item-action | itemId, dateType, dateRange | 用户未给商品 ID 或时间 |

### 缺失检测逻辑

1. **时间缺失**（dateType + dateRange）：用户未提到任何时间范围
2. **商品 ID 缺失**（itemId）：用户想做单品下钻但未提供商品 ID
3. **指标缺失**（indexCode）：用户想做趋势分析但未指定看哪个指标
4. **分析维度缺失**：用户说"分析某个商品"但未指定具体看什么（流量/SKU/搜索词等）

---

## Step 4: 参数收集（ask_user_question 问题模板）

### 设计原则

- **批量提问**：将所有缺失参数合并到一次 `ask_user_question` 调用中，减少交互轮次
- **提供推荐选项**：每个问题提供 2-4 个选项，推荐项放第一位并标注"(推荐)"
- **选项附说明**：每个选项的 description 解释其含义
- **最多 4 个问题**：单次 ask_user_question 最多提 4 个问题，避免用户疲劳

### 问题模板

#### 问题 A：时间范围（当 dateType/dateRange 缺失时）

```
header: "时间范围"
question: 您想查看哪个时间范围的商品数据？（数据为离线口径，最新为昨天）
options:
  - label: "昨天（推荐）"
    description: "查看昨天（2026-06-21）的单日数据，指标最全"
  - label: "近 7 天"
    description: "查看最近 7 天（2026-06-15 至 2026-06-21）的汇总数据"
  - label: "近 30 天"
    description: "查看最近 30 天（2026-05-23 至 2026-06-21）的汇总数据"
  - label: "上个月"
    description: "查看 2026 年 5 月整月数据"
```

#### 问题 B：商品 ID（当 itemId 缺失但用户想做单品下钻时）

```
header: "目标商品"
question: 您想分析哪个商品？请提供商品 ID（可在商品排行榜中查看）
options: []  // 纯文本输入，用户输入商品 ID
```

> 注意：如果用户没有商品 ID，建议先执行 all-items 获取商品列表，再让用户选择。

#### 问题 C：分析维度（当用户想做单品分析但未指定具体维度时）

```
header: "分析维度"
question: 您想查看该商品的哪些数据？
options:
  - label: "核心指标概览（推荐）"
    description: "查看支付金额、买家数、件数等核心销售指标及环比"
  - label: "流量来源"
    description: "查看 Top10 流量来源渠道分布"
  - label: "SKU 销售"
    description: "查看 Top5 SKU 的销售件数和占比"
  - label: "搜索词"
    description: "查看 Top10 搜索词，了解用户搜什么词找到该商品"
  - label: "指标趋势"
    description: "查看某个指标的时间序列趋势（需指定具体指标）"
  - label: "运营动作效果"
    description: "查看短视频带货、新客引导、营销活动等运营动作数据"
```

> 注意：此问题支持多选（multiSelect: true），用户可同时选择多个维度。

#### 问题 D：趋势指标（当工具为 item-trend 但 indexCode 缺失时）

```
header: "趋势指标"
question: 您想查看哪个指标的趋势变化？
options:
  - label: "支付金额（推荐）"
    description: "查看支付金额随时间的变化趋势"
  - label: "访客数"
    description: "查看商品访客数随时间的变化趋势"
  - label: "支付转化率"
    description: "查看支付转化率随时间的变化趋势"
  - label: "支付买家数"
    description: "查看支付买家数随时间的变化趋势"
```

#### 问题 E：排序方式（当用户未指定 orderBy 且意图为列表查询时）

```
header: "排序方式"
question: 您希望商品按什么指标排序？
options:
  - label: "支付金额（推荐）"
    description: "按支付金额降序排列，看哪些商品卖得最好"
  - label: "支付件数"
    description: "按销量降序排列"
  - label: "访客数"
    description: "按访客数降序排列，看哪些商品流量最大"
  - label: "支付转化率"
    description: "按转化率降序排列，看哪些商品转化效率最高"
```

### 提问组合策略

| 缺失场景 | 提问组合 |
|---------|---------|
| 列表查询，时间缺失 | 问题 A |
| 列表查询，时间 + 排序缺失 | 问题 A + 问题 E |
| 单品下钻，商品 ID + 时间缺失 | 问题 B + 问题 A |
| 单品下钻，商品 ID + 时间 + 维度缺失 | 问题 B + 问题 A + 问题 C |
| 趋势分析，商品 ID + 时间 + 指标缺失 | 问题 B + 问题 A + 问题 D |
| 意图不明确 | 意图确认问题 + 问题 A |

---

## Step 5: 组装并传递给 sycm-agent

### 传递规范

1. **用户原始请求必须完整、未做修改地传递**
2. **已确认的参数以结构化清单附加在用户请求之后**
3. **通过 `agent_task(agent_type="sycm-agent")` 调用**
4. **不在 prompt 中编造用户未提及的需求**

### Prompt 拼装格式

```
用户原始请求：
{用户原始语句，一字不改}

已确认参数：
- 工具：{tool_name}
- dateType：{dateType}
- dateRange：{dateRange}
- itemId：{itemId（如有）}
- 视角：{拆分/整体}
- device：{device}
- orderBy：{orderBy}
- order：{order}
- compareType：{compareType（如有）}
- indexCode：{indexCode（如有）}
- pageSize：{pageSize}
- keyword：{keyword（如有）}

请使用 sycm-cc-item-rank 技能的 {tool_name} 工具执行上述查询，并按用户原始请求的意图返回结果。
```

### 调用示例

```python
agent_task(
    agent_type="sycm-agent",
    description="""
用户原始请求：
帮我看看昨天店铺里卖得最好的5个商品，它们的流量都是从哪来的？

已确认参数：
- 工具：all-items（列表）+ item-flow（下钻）
- dateType：day
- dateRange：2026-06-21|2026-06-21
- 视角：拆分（默认）
- device：0（全部终端）
- orderBy：payAmt
- order：desc
- pageSize：5

执行步骤：
1. 先调 all-items 获取 Top5 商品及 itemId
2. 对每个 itemId 并行调 item-flow 获取流量来源 Top10
3. 合并结果返回

请使用 sycm-cc-item-rank 技能执行上述查询。
"""
)
```

---

## 典型场景决策路径

### 场景 1：用户说"帮我看看昨天商品排行"

```
意图识别 → all-items（拆分视角，默认）
参数提取 → dateType=day, dateRange=2026-06-21|2026-06-21
缺失检测 → 无缺失（orderBy 用默认 payAmt，pageSize 用默认 10）
→ 直接传递给 sycm-agent
```

### 场景 2：用户说"帮我看看商品数据"

```
意图识别 → 不明确
→ ask_user_question: 意图确认问题 + 问题 A（时间范围）
→ 用户选择"商品排行榜" + "昨天"
→ all-items, dateType=day, dateRange=2026-06-21|2026-06-21
→ 传递给 sycm-agent
```

### 场景 3：用户说"分析商品 675099575218 的流量"

```
意图识别 → item-flow
参数提取 → itemId=675099575218
缺失检测 → dateType/dateRange 缺失
→ ask_user_question: 问题 A（时间范围）
→ 用户选择"近 7 天"
→ item-flow, itemId=675099575218, dateType=recent7, dateRange=2026-06-15|2026-06-21
→ 传递给 sycm-agent
```

### 场景 4：用户说"看看这个商品怎么样"

```
意图识别 → 不明确（单品分析但未指定维度）
缺失检测 → itemId 缺失 + dateType/dateRange 缺失 + 分析维度缺失
→ ask_user_question: 问题 B（商品 ID）+ 问题 A（时间范围）+ 问题 C（分析维度）
→ 用户输入 itemId + 选择时间 + 选择维度
→ 根据用户选择的维度确定具体工具
→ 传递给 sycm-agent
```

### 场景 5：用户说"昨天推广商品花了多少钱"

```
意图识别 → dmp-items
参数提取 → dateType=day, dateRange=2026-06-21|2026-06-21
缺失检测 → 无缺失
→ 直接传递给 sycm-agent
```

### 场景 6：用户说"看看商品 123456 的支付金额趋势"

```
意图识别 → item-trend
参数提取 → itemId=123456, indexCode=payAmt
缺失检测 → dateType/dateRange 缺失
→ ask_user_question: 问题 A（时间范围）
→ 用户选择"近 30 天"
→ item-trend, itemId=123456, dateType=recent30, dateRange=2026-05-23|2026-06-21, indexCode=payAmt
→ 传递给 sycm-agent
```

---

## 重要约束

1. **不编造数据**：所有参数必须来自用户语句或 ask_user_question 的回答，不可自行猜测
2. **不修改用户原始请求**：传递给 sycm-agent 时，用户原始语句必须一字不改
3. **不跳过参数收集**：缺失必填参数时必须通过 ask_user_question 确认，不可使用默认值代替用户决策（时间范围除外，可推荐但需确认）
4. **不直接调用 CLI**：本技能不执行 sycm-cc-item-rank 的 CLI 命令，只负责参数收集和传递
5. **不二次处理结果**：sycm-agent 返回的结果直接传达给用户，不做额外加工
