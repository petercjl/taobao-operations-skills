#!/usr/bin/env node
import fs from 'node:fs';

function numberOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value && typeof value === 'object' && 'value' in value ? value.value : value);
  return Number.isFinite(number) ? number : null;
}

function keywordsOf(value) {
  if (typeof value === 'string') return value.split(/[,，、|/\s]+/u).map((word) => word.trim()).filter(Boolean);
  if (Array.isArray(value)) return value.flatMap(keywordsOf);
  if (value && typeof value === 'object') return Object.values(value).flatMap(keywordsOf);
  return [];
}

function compact(row) {
  const uv = numberOf(row.uv);
  const payByrCnt = numberOf(row.payByrCnt);
  return {
    rank: numberOf(row.rank),
    rankComparison: numberOf(row.rankCycleCqc),
    itemId: row.itemId === null || row.itemId === undefined ? null : String(row.itemId),
    title: row.title ?? null,
    shopTitle: row.shopTitle ?? null,
    detailUrl: row.detailUrl ?? null,
    pictureUrl: row.pictUrl ?? null,
    payByrCnt,
    uv,
    searchUv: numberOf(row.searchUv),
    cartByrCnt: numberOf(row.cartByrCnt),
    collectByrCnt: numberOf(row.cltByrCnt),
    buyerVisitorRatio: payByrCnt === null || uv === null || !uv ? null : payByrCnt / uv,
    coreKeywords: [...new Set(keywordsOf(row.coreKeywords))]
  };
}

export function analyzeBestSellingItems(input, { store = null, limit = 20 } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Item-rank input must be a JSON object.');
  const data = input.data?.items ? input.data : input;
  const items = (Array.isArray(data.items) ? data.items : []).map(compact).filter((row) => row.itemId || row.title);
  const requested = numberOf(data.targetTopN) ?? limit;
  const warnings = Array.isArray(data.warnings) ? data.warnings : [];
  const stoppedBy = data.stoppedBy ?? null;
  const expectedCount = Math.min(requested, numberOf(data.recordCount) ?? requested);
  const cleanStop = ['targetTopN', 'shortPage', 'emptyPage'].includes(stoppedBy);
  const completeness = {
    requested,
    returnedCount: items.length,
    recordCount: numberOf(data.recordCount),
    fetchedPages: numberOf(data.fetchedPages),
    stoppedBy,
    duplicateCount: numberOf(data.duplicateCount) ?? 0,
    completeForRequestedTop: items.length >= expectedCount && cleanStop && warnings.length === 0,
    warnings
  };
  const counts = new Map();
  for (const item of items) for (const word of item.coreKeywords) counts.set(word, (counts.get(word) ?? 0) + 1);
  const keywordFrequency = [...counts.entries()].map(([keyword, itemCount]) => ({ keyword, itemCount, itemShare: items.length ? itemCount / items.length : null })).sort((a, b) => b.itemCount - a.itemCount || a.keyword.localeCompare(b.keyword, 'zh-CN')).slice(0, limit);
  const shops = new Map();
  for (const item of items) if (item.shopTitle) shops.set(item.shopTitle, (shops.get(item.shopTitle) ?? 0) + 1);
  const shopDistribution = [...shops.entries()].map(([shopTitle, itemCount]) => ({ shopTitle, itemCount, itemShare: items.length ? itemCount / items.length : null })).sort((a, b) => b.itemCount - a.itemCount || a.shopTitle.localeCompare(b.shopTitle, 'zh-CN'));
  const topItems = [...items].sort((a, b) => (a.rank ?? Number.MAX_SAFE_INTEGER) - (b.rank ?? Number.MAX_SAFE_INTEGER)).slice(0, limit);
  const actions = [];
  if (keywordFrequency[0]) actions.push(`核心关键词“${keywordFrequency[0].keyword}”覆盖 ${keywordFrequency[0].itemCount} 个 Top 商品：用于标题和竞品样本分组研究；下一步核对该词下商品访客与支付买家。`);
  if (shopDistribution[0]?.itemCount > 1) actions.push(`${shopDistribution[0].shopTitle} 在本次 Top 列表占 ${shopDistribution[0].itemCount} 席：优先下钻其重复上榜商品的共同定位；不要把上榜席位直接解释为市场份额。`);
  if (topItems[0]) actions.push(`先以排名第 1 的商品作为基准样本，再与第 2～${Math.min(5, topItems.length)} 名比较标题关键词、访客与支付买家；保留平台未返回指标为数据缺口。`);
  const dataGaps = ['Ranking rows do not provide exact GMV, price, cost, profit, or market share unless those fields are explicitly returned.', 'Keyword co-occurrence and buyer/visitor ratio are descriptive signals, not proof of purchase causality or the platform conversion metric.'];
  if (!completeness.completeForRequestedTop) dataGaps.unshift('The requested Top N collection is incomplete.');
  return {
    store: store ?? input.store ?? null,
    categoryId: data.cateId ?? null,
    dateRange: data.dateRange ?? null,
    rankType: data.rankType ?? null,
    completeness,
    topItems,
    keywordFrequency,
    shopDistribution,
    actions: actions.slice(0, 3),
    dataGaps,
    methodology: 'category-best-selling-items-v1'
  };
}

function parseArgs(argv) {
  const options = { limit: 20 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--input') options.input = argv[++index];
    else if (argv[index] === '--store') options.store = argv[++index];
    else if (argv[index] === '--limit') options.limit = Number(argv[++index]);
  }
  if (!options.input) throw new Error('--input is required.');
  if (!Number.isInteger(options.limit) || options.limit < 1 || options.limit > 200) throw new Error('--limit must be an integer from 1 to 200.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    process.stdout.write(`${JSON.stringify(analyzeBestSellingItems(JSON.parse(fs.readFileSync(options.input, 'utf8')), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'CATEGORY_BEST_SELLING_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
