---
name: category-top-shops-profile
description: 分析指定类目头部商品背后的店铺集中度、重复上榜、排名变化与店铺经营特征。适用于“这个类目哪些店铺最强”“头部店铺画像”“增长店铺与落榜店铺”等请求。
---

# 类目头部店铺画像

本 Skill 做店铺维度的聚合与解释。榜单取数由 `category-best-selling-items-analysis` 完成；本 Skill 不调用远程 Agent，也不猜测未返回的店铺规模、品牌归属或成交额。

## 依赖与输入

- 精确依赖 Skill：`category-best-selling-items-analysis`，最低契约版本 3。
- 底层依赖：`@petercjl/sycmcli >= 0.4.0`，能力 `sycm.market.item_rank.read`。
- 输入：`store`、叶子类目 `cateId`、`dateType`、`dateRange`、`rankType`、`topN`；可选对比期榜单。
- 运行时必须加载依赖 Skill 的当前 `SKILL.md`，按其主线取得完整、可追溯的榜单结果，再返回本主线。

## 主线

1. 唯一解析店铺和叶子类目；类目或店铺不唯一时停止并澄清。
2. 调用 `category-best-selling-items-analysis` 获取目标榜单，保留完整性、排名、商品 ID、店铺名与平台比较值。
3. 按店铺名精确聚合：上榜商品数、榜单份额、最佳名次、名次中位数、核心关键词、样本商品。
4. 若有同口径对比期，按稳定店铺标识或精确店铺名计算新增、持续、退出和名次变化；无对比期时不声称“增长”或“落榜”。
5. 输出头部集中度、重复上榜店铺、店铺类型特征和最多 3 条可执行建议。榜单不完整时所有份额标为“已取样本内”。

确定性聚合使用 `node scripts/analyze.mjs` 对应导出的 `profileTopShops()`；语义层不得自行重复计算店铺份额。

## 输出

`categoryId`、`dateRange`、`rankType`、`completeness`、`shopCount`、`topShops[]`、`concentration`、`movement`、`shopPatterns[]`、`sampleItems[]`、`actions[]`、`dataGaps[]`。

## 恢复与边界

- 登录或风控：由 sycmcli 打开对应店铺浏览器，用户完成验证后仅重试一次。
- 空榜单：返回空结果与真实口径，不生成画像。
- 店铺名缺失或模糊：归入“店铺信息缺失”，不自动合并。
- 只读；不关注/取消关注店铺，不修改监控列表；完成后删除临时经营数据。

## 验收

- 每个店铺结论能回指到榜单商品；商品只计入一个店铺。
- 对比期口径一致，`null` 未改成 0。
- 不完整榜单没有被描述为全市场份额。
