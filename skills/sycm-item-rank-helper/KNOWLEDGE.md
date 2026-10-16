# 参数参考手册

本文件是 `sycm-item-rank-helper` 技能的参数知识库，涵盖 `sycm-cc-item-rank` 全部 11 个工具的参数定义、枚举值、日期计算规则和边界条件。

---

## 一、工具完整清单（11 个）

### 主表（列表数据，5 个）

| 工具 | 功能 | 视角 | 指标数 | 必填参数 | 常用可选参数 | orderBy 默认 |
|------|------|------|--------|----------|-------------|-------------|
| `all-items` | 全部商品排行 | 拆分 | 32 | dateType, dateRange | page, pageSize, orderBy, order, device, compareType, keyword, cateId, cateLevel, guideCateId, tag | `payAmt` |
| `all-items-whole` | 全部商品排行 | 整体 | 6 | dateType, dateRange | page, pageSize, orderBy, order, device, keyword, cateId, cateLevel, guideCateId, tag | `payAmt` |
| `my-items` | 我关注的商品 | 拆分 | 32 | dateType, dateRange | page, pageSize, orderBy, order, device, compareType, keyword | `payAmt` |
| `my-items-whole` | 我关注的商品 | 整体 | 6 | dateType, dateRange | page, pageSize, orderBy, order, device, keyword | `payAmt` |
| `dmp-items` | 推广商品排行 | — | 11 | dateType, dateRange | page, pageSize, orderBy, order, itemId | `fCharge` |

### 单品下钻（6 个，均需要 itemId）

| 工具 | 功能 | 必填参数 | 常用可选参数 | 说明 |
|------|------|----------|-------------|------|
| `item-overview` | 核心指标概览（当期值 + 环比） | itemId, dateType, dateRange | — | 单品核心销售指标 |
| `item-trend` | 指标趋势时间序列 | itemId, dateType, dateRange, indexCode | type(默认1), device(默认0) | 必须指定 indexCode |
| `item-flow` | 流量来源 Top10 | itemId, dateType, dateRange | — | 固定 page=1, pageSize=10, order=desc |
| `item-sku` | SKU 销售 Top5 | itemId, dateType, dateRange | pageSize | 固定 indexCode=payItmCnt |
| `item-searchword` | 搜索词 Top10 | itemId, dateType, dateRange | — | 固定 page=1, pageSize=10, order=desc |
| `item-action` | 运营动作效果 | itemId, dateType, dateRange | — | 固定 page=1, pageSize=10, 无 orderBy |

---

## 二、枚举值速查

### dateType（日期类型）

| 值 | 中文 | 说明 |
|----|------|------|
| `day` | 某一天 | dateRange 填单日，指标最全（含月累计/年累计/价格力星级/件单价） |
| `week` | 某一周 | 去掉月累计/年累计/价格力星级/件单价 |
| `month` | 某一月 | 去掉日周期独有项，增加竞争力评分 diagScore |
| `recent7` | 近 7 天 | 同 week 的可见性 |
| `recent30` | 近 30 天 | 同 week 的可见性 |
| ~~today~~ | ~~今日实时~~ | 不支持，离线口径 T-1 |
| ~~compareRange~~ | ~~自定义周期~~ | 不支持 |

### device（终端类型）

| 值 | 中文 |
|----|------|
| `0` | 全部终端（默认） |
| `1` | PC 端 |
| `2` | 无线端 |

### compareType（对比类型，仅 all-items / my-items）

| 值 | 中文 |
|----|------|
| `cycle` | 较上一周期（默认） |
| `dailyAvg` | 较日常平均 |
| `cmptItem` | 较同类商品 |

### order（排序方向）

| 值 | 含义 |
|----|------|
| `desc` | 降序（默认） |
| `asc` | 升序 |

### itemRankActiveKey（主 Tab）

| 值 | 中文 | 对应工具 |
|----|------|---------|
| `all` | 全部商品 | all-items / all-items-whole |
| `dmp` | 推广商品 | dmp-items |
| `my` | 我关注的商品 | my-items / my-items-whole |

---

## 三、日期计算规则

### 核心规则

- 所有接口为**离线口径（T-1）**，用户问"今天"数据时需提示并改问昨天
- `dateRange` 格式：`YYYY-MM-DD|YYYY-MM-DD`（含竖线，需用引号包裹）
- 当前日期为 2026-06-22，以下计算基于此日期

### 自然语言 → dateType + dateRange 映射

| 用户说法 | dateType | dateRange 计算方式 | 示例（基于 2026-06-22） |
|---------|----------|-------------------|----------------------|
| 昨天 | `day` | T-1 单日 | `2026-06-21|2026-06-21` |
| 前天 | `day` | T-2 单日 | `2026-06-20|2026-06-20` |
| 近 7 天 / 最近一周 | `recent7` | T-1 往前推 7 天 | `2026-06-15|2026-06-21` |
| 近 30 天 /最近一个月 | `recent30` | T-1 往前推 30 天 | `2026-05-23|2026-06-21` |
| 上周 | `week` | 上周一到周日 | `2026-06-15|2026-06-21`（需确认上周定义） |
| 上个月 | `month` | 上月 1 日到月末 | `2026-05-01|2026-05-31` |
| 某一天（用户指定日期） | `day` | 用户指定日期 | `2026-06-15|2026-06-15` |
| 某一周（用户指定周） | `week` | 用户指定周的起止 | 需确认具体日期范围 |
| 某一月（用户指定月） | `month` | 用户指定月的 1 日到月末 | `2026-05-01|2026-05-31` |

### 注意事项

- 用户说"今天"→ 提示离线口径 T-1，建议改查"昨天"
- 用户说"最近"但未指定天数 → 默认推荐"近 7 天"
- 用户说"上周"但未指定具体日期 → 需确认是自然周（周一到周日）还是最近 7 天
- 用户说"上个月"但未指定月份 → 默认上一个自然月

---

## 四、视角差异说明

### 业务区别

淘宝商品分**主商品**和**渠道品**两种类型：
- **主商品**：店铺标准链接
- **渠道品**：挂靠在主商品下的副链接（分销/促销/活动等场景用）

| 视角 | 对应工具 | 数据口径 | 展示粒度 | 指标数 |
|------|---------|---------|---------|--------|
| **整体视角** | all-items-whole / my-items-whole | 主商品 + 渠道品汇总统计 | 每主商品一行 | 6 |
| **拆分视角** | all-items / my-items | 主商品、渠道品各自独立统计 | 主商品 + 每个渠道品各一行 | 32 |

### 使用场景

- **整体视角**：看"店铺卖得最好的商品"/"日常经营看板"/"商品总成交（含渠道品）"
- **拆分视角**：看"主商品链接本身真实表现"/"渠道品分开看"/"不含渠道品"

### 默认规则

**当用户没有强调要使用整体视角时，默认使用拆分视角**，以获取更多指标（32 个 vs 6 个）。

### 两视角字段命名差异（关键）

| 业务含义 | 整体视角 code | 拆分视角 code |
|---------|-------------|-------------|
| 支付金额 | `payAmt` | `payAmt` |
| 支付买家数 | `payByrCntIndexFree` | `payByrCnt` |
| 支付商品件数 | `payOrdItemQty` | `payItmCnt` |
| 客单价 | `perByrAmt` | `payPct` |
| 件单价 | `perItemAmt` | `itemUnitPrice1` |

---

## 五、orderBy 排序限制

### 可排序字段

orderBy 必须取自对应视角的返回指标 code 列表。

### 不可排序字段

以下字段**不可作为 orderBy 排序**（前端兜底转 `payAmt`）：

| code | 中文 | 所属视角 |
|------|------|---------|
| `itemStatus` | 商品状态 | 拆分 |
| `starLevel001` | 价格力星级 | 拆分 |
| `itemUnitPrice1` | 件单价 | 拆分 |

### 常用排序字段

| 用户意图 | orderBy code | 说明 |
|---------|-------------|------|
| 按销售额排 | `payAmt` | 默认排序 |
| 按销量排 | `payItmCnt`（拆分）/ `payOrdItemQty`（整体） | 支付件数 |
| 按访客排 | `itmUv` | 仅拆分视角 |
| 按转化率排 | `payRate` | 仅拆分视角 |
| 按推广花费排 | `fCharge` | dmp-items 默认 |

---

## 六、拆分视角 32 指标分组

### 商品动销（14 个）

| 中文 | code |
|------|------|
| 支付金额 | `payAmt` |
| 总支付金额 | `subPayOrdAmt` |
| 成功退款金额 | `sucRefundAmt` |
| 支付件数 | `payItmCnt` |
| 总支付商品件数 | `subPayOrdItmQty` |
| 支付买家数 | `payByrCnt` |
| 支付转化率 | `payRate` |
| 支付新买家数 | `newPayByrCnt` |
| 支付老买家数 | `payOldByrCnt` |
| 老买家支付金额 | `olderPayAmt` |
| 聚划算支付金额 | `juPayAmt` |
| 月累计支付金额 | `mtdPayAmt` |
| 月累计支付件数 | `mtdPayItmCnt` |
| 年累计支付金额 | `ytdPayAmt` |

### 商品状态（1 个）

| 中文 | code |
|------|------|
| 商品状态 | `itemStatus`（不可排序） |

### 商品转化（13 个）

| 中文 | code |
|------|------|
| 商品加购件数 | `itemCartCnt` |
| 商品加购人数 | `itemCartByrCnt` |
| 商品收藏人数 | `itemCltByrCnt` |
| 访问加购转化率 | `visitCartRate` |
| 访问收藏转化率 | `visitCltRate` |
| 商品访客数 | `itmUv` |
| 商品浏览量 | `itmPv` |
| 平均停留时长 | `itmStayTime` |
| 商品详情页跳出率 | `itmBounceRate` |
| 搜索引导访客数 | `seGuideUv` |
| 搜索引导支付买家数 | `seGuidePayByrCnt` |
| 搜索引导支付转化率 | `seGuidePayRate` |
| 访客平均价值 | `uvAvgValue` |

### 商品价格（2 个，仅 day 周期）

| 中文 | code |
|------|------|
| 价格力星级 | `starLevel001`（不可排序） |
| 件单价 | `itemUnitPrice1`（不可排序） |

### 商品推广（2 个）

| 中文 | code |
|------|------|
| 推广消耗 | `fCharge` |
| 推广直接 ROI | `pDROI` |

---

## 七、整体视角 6 指标

| 中文 | code | 说明 |
|------|------|------|
| 支付金额 | `payAmt` | 默认排序 |
| 支付买家数 | `payByrCntIndexFree` | 整体视角专用 |
| 支付商品件数 | `payOrdItemQty` | — |
| 支付子订单数 | `payOrdCnt` | — |
| 客单价 | `perByrAmt` | — |
| 件单价 | `perItemAmt` | — |

---

## 八、推广专属 11 指标（dmp-items）

| 中文 | code |
|------|------|
| 推广消耗（默认排序） | `fCharge` |
| 直接引导成交金额 | `alipayDirAmt` |
| 推广直接 ROI | `pDROI` |
| 展现量 | `fImpression` |
| 点击量 | `click` |
| 点击率 | `fClickRate` |
| 单次点击成本 | `cpc` |
| 直接成交笔数 | `dOrdCnt` |
| 总成交金额 | `tPAmt` |
| 总 ROI | `tROI` |
| 总成交笔数 | `tOrdCnt` |

---

## 九、单品下钻工具指标

### item-flow / item-searchword

| code | 中文 | 可见范围 |
|------|------|---------|
| `uv` | 访客数 | 所有周期，默认排序 |
| `cartByrCnt` | 加购人数 | 仅 day |
| `payRate` | 支付转化率 | 所有周期 |

### item-sku

| code | 中文 | 说明 |
|------|------|------|
| `payItmCnt` | 支付件数 | 离线唯一可用 indexCode |
| `payAmtRatio` | 支付金额占比 | 响应字段，非 indexCode 控制 |

### item-action 动作 ID

| actionId | 动作名 | 前端展示文案 |
|----------|--------|-------------|
| `fscreen` | 首屏短视频带货 | "播放人数 {playUv}" |
| `450` | 流量返场-新客引导 | "引导新客人数 {guideNewUv}" |
| `fqm` | 营销活动引导 | "引导支付金额 {payOrdAmtStage}" |

### item-trend

- 必须指定 `--indexCode`（指标 code），如 `payAmt`、`itmUv`、`payRate` 等
- `--type` 默认 1，`--device` 默认 0
- dateType=day 时 dateRange 填单日；跨天用 recent7/recent30

---

## 十、边界条件

| 情况 | 处理方式 |
|------|---------|
| 用户问"今天"数据 | 提示离线口径 T-1，建议改查"昨天" |
| 用户想看推广数据但 dateType=today | dmp-items 不支持 today，改推其他日期 |
| 用户想下钻但没给 itemId | 先调主表（all-items 等）拿列表，让用户选择商品 |
| dateType 不支持 | 提示仅支持 day/week/month/recent7/recent30 |
| 用户未指定时间范围 | 默认推荐"昨天"（day）或"近 7 天"（recent7） |
| 用户未指定视角 | 默认使用拆分视角（32 指标） |
| 用户未指定终端 | 默认全部终端（device=0） |
| 用户未指定排序 | 使用工具默认 orderBy |
| 用户未指定翻页 | 默认 page=1, pageSize=10 |

---

## 十一、典型用户意图 → 工具映射

| 用户意图关键词 | 推荐工具 | 说明 |
|--------------|---------|------|
| 商品排行 / 卖得最好 / 销量排名 | all-items | 拆分视角，32 指标 |
| 商品总成交（含渠道品） | all-items-whole | 整体视角，6 指标 |
| 我关注的商品 | my-items / my-items-whole | 按视角选择 |
| 推广商品 / 直通车 / 万相台 | dmp-items | 推广 11 指标 |
| 单品概览 / 核心指标 | item-overview | 需 itemId |
| 单品趋势 / 指标走势 | item-trend | 需 itemId + indexCode |
| 流量来源 / 流量从哪来 | item-flow | 需 itemId |
| SKU 销售 / 哪个规格卖得好 | item-sku | 需 itemId |
| 搜索词 / 用户搜什么词 | item-searchword | 需 itemId |
| 运营动作 / 短视频带货 / 新客引导 | item-action | 需 itemId |
