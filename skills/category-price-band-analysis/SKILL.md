---
name: category-price-band-analysis
description: 分析淘宝或天猫指定叶子类目的平台价格带，并读取各价格带的头部商品样本。适用于“类目有哪些价格带”“不同价位卖什么”“价格带选品研究”等请求。
---

# 类目价格带分析

本 Skill 负责价格带研究口径、跨价格带样本比较和业务解读。价格带定义、排行取数、店铺身份校验和登录恢复由 `sycmcli` 提供。

## 运行依赖

- 逻辑依赖名：`sycmcli`
- npm 包：`@petercjl/sycmcli`，最低版本 `0.4.0`
- 宿主必需能力：`command.execute`
- sycmcli 必需能力：`sycm.category.read`、`sycm.market.price_segments.read`、`sycm.market.item_rank.read`
- 解析方式：按精确名称从宿主 Skill 目录加载 `sycmcli`；若未发现，执行 `sycmcli skill source --json` 获取 canonical source。完整读取其 `SKILL.md` 后执行。
- 兼容判断：确认版本不低于 `0.4.0`，并检查三项必需能力。
- 缺失处理：返回 `DEPENDENCY_MISSING` 或 `CAPABILITY_UNAVAILABLE`，提示安装或更新 `@petercjl/sycmcli`。

## 输入

- `store`：已授权店铺别名或显示名称。
- `categoryId`：叶子类目 ID；与 `categoryName` 至少提供一项。
- `categoryName`：用于解析叶子类目的名称或关键词。
- `dateType`：`day`、`recent7` 或 `recent30`，默认 `recent7`。
- `dateRange`：可选，格式 `YYYY-MM-DD|YYYY-MM-DD`。
- `samplePerBand`：每个价格带读取的头部商品数，默认 5，范围 1～20。

## 主线

### 1. 校验依赖、店铺和叶子类目

加载当前 `sycmcli` Skill，验证版本与能力；运行 `sycmcli stores list` 解析唯一店铺。用户只给类目名称时执行：

```bash
sycmcli category search --store <alias> --keyword <类目名称>
```

仅使用唯一或用户明确选择的叶子类目。

### 2. 获取平台价格带

创建权限受限的临时目录，运行：

```bash
sycmcli price segments \
  --store <alias> \
  --cate-id <leaf-category-id> \
  --date-type <type> \
  --out <temp>/segments.json
```

用户指定周期时追加 `--date-range <START|END>`。价格带的边界、开区间属性和 ID 以平台返回为准。

### 3. 获取各价格带头部样本

按 `segments.json` 中每个 `priceSegId` 串行执行：

```bash
sycmcli item rank \
  --store <alias> \
  --cate-id <leaf-category-id> \
  --price-seg <price-segment-id> \
  --rank-type gmv \
  --date-type <type> \
  --top <samplePerBand> \
  --out <temp>/rank-<price-segment-id>.json
```

每份结果的 `filters.priceSeg` 必须等于文件对应的价格带 ID。任一组不匹配时停止分析，返回 `PRICE_SEGMENT_TRACE_MISMATCH`。

### 4. 生成确定性底稿

```bash
node scripts/analyze.mjs \
  --segments <temp>/segments.json \
  --rankings-dir <temp> \
  --store <alias> \
  --sample-per-band <N>
```

脚本输出平台价格带、各带样本完整性、头部商品、支付买家与访客区间分布以及数据缺口。区间值保持原样，不换算中点。

### 5. 业务解读

1. 先说明类目、周期、平台价格带数量和样本口径。
2. 分价格带展示头部商品、店铺与实际返回指标。
3. 比较不同价格带的商品定位和头部样本结构；样本排行不能代表整个价格带的规模或份额。
4. 输出最多 3 条选品、定价验证或竞品下钻建议，每条引用具体价格带和样本证据。

## 输出契约

```json
{
  "store": "店铺别名",
  "categoryId": "叶子类目ID",
  "dateRange": "YYYY-MM-DD|YYYY-MM-DD",
  "samplePerBand": 5,
  "bands": [],
  "actions": [],
  "dataGaps": []
}
```

## 异常与恢复

- `AUTH_REQUIRED`、`AUTH_OR_RISK_CHALLENGE`：运行 `sycmcli auth login --store <alias>`，让用户在对应可见 Chrome 中完成登录或验证；确认后重试一次。
- `STORE_IDENTITY_MISMATCH`：立即停止，不重绑、不切换店铺。
- 类目候选不唯一：请用户选择叶子类目。
- 某价格带排行为空：保留空样本，不虚构商品或结论。
- 指标为 `null`：保留缺失语义，不参与比较。

## 边界

- 只读，不修改商品价格、促销、广告或库存。
- 价格带排行样本不等于价格带成交额、市场规模、份额、利润或最优定价。
- 平台返回区间不转换为精确数值，不基于区间中点生成机会分。
- 完成后删除临时经营数据。

## 验收

- 店铺、叶子类目、周期和价格带来源可追溯。
- 每个排行结果与价格带 ID 匹配。
- 每组样本完整性、告警和缺失值明确。
- 建议有价格带与商品样本证据，且不超过 3 条。
- 临时经营数据已清理。
