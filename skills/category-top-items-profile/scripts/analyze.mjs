#!/usr/bin/env node
import fs from 'node:fs';

function numberOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function profileTopItems(input, { limit = 20 } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Upstream analysis must be a JSON object.');
  const required = ['completeness', 'topItems', 'keywordFrequency', 'shopDistribution', 'dataGaps'];
  for (const field of required) if (!(field in input)) throw new Error(`CONTRACT_MISMATCH: upstream output is missing ${field}.`);
  if (!Array.isArray(input.topItems) || !Array.isArray(input.keywordFrequency) || !Array.isArray(input.shopDistribution)) throw new Error('CONTRACT_MISMATCH: upstream list fields must be arrays.');
  const topItems = input.topItems.slice(0, limit).map((row) => ({
    rank: numberOf(row.rank),
    rankComparison: numberOf(row.rankComparison),
    itemId: row.itemId ?? null,
    title: row.title ?? null,
    shopTitle: row.shopTitle ?? null,
    payByrCnt: numberOf(row.payByrCnt),
    uv: numberOf(row.uv),
    searchUv: numberOf(row.searchUv),
    cartByrCnt: numberOf(row.cartByrCnt),
    collectByrCnt: numberOf(row.collectByrCnt),
    coreKeywords: Array.isArray(row.coreKeywords) ? row.coreKeywords : []
  }));
  const rankMovementSummary = { positiveComparison: 0, negativeComparison: 0, zeroComparison: 0, unavailable: 0 };
  for (const item of topItems) {
    if (item.rankComparison === null) rankMovementSummary.unavailable += 1;
    else if (item.rankComparison > 0) rankMovementSummary.positiveComparison += 1;
    else if (item.rankComparison < 0) rankMovementSummary.negativeComparison += 1;
    else rankMovementSummary.zeroComparison += 1;
  }
  const positioningKeywords = input.keywordFrequency.slice(0, limit).map((row) => ({ keyword: row.keyword ?? null, itemCount: numberOf(row.itemCount), itemShare: numberOf(row.itemShare) })).filter((row) => row.keyword);
  const recurringShops = input.shopDistribution.filter((row) => numberOf(row.itemCount) > 1).map((row) => ({ shopTitle: row.shopTitle ?? null, itemCount: numberOf(row.itemCount), itemShare: numberOf(row.itemShare) }));
  const complete = input.completeness?.completeForRequestedTop === true;
  const actions = [];
  if (positioningKeywords[0]) actions.push(`以平台核心关键词“${positioningKeywords[0].keyword}”覆盖的 ${positioningKeywords[0].itemCount} 个 Top 商品建立第一组竞品样本，逐个核对商品定位和实际详情。`);
  if (recurringShops[0]) actions.push(`${recurringShops[0].shopTitle} 在本次样本重复上榜 ${recurringShops[0].itemCount} 席：比较这些商品的共同定位；席位数不解释为市场份额。`);
  if (topItems.length) actions.push(`以第 1～${Math.min(5, topItems.length)} 名为核心样本，结合平台核心关键词和实际返回指标制定标题研究清单；未返回的属性、评价和价格另行取证。`);
  const dataGaps = [...input.dataGaps];
  if (!complete) dataGaps.unshift('The upstream Top N ranking is incomplete; this profile is partial.');
  return {
    status: complete ? 'success' : 'partial',
    store: input.store ?? null,
    categoryId: input.categoryId ?? null,
    dateRange: input.dateRange ?? null,
    rankType: input.rankType ?? null,
    sample: { requested: input.completeness?.requested ?? null, profiled: topItems.length, completeForRequestedTop: complete },
    topItems,
    positioningKeywords,
    recurringShops,
    rankMovementSummary,
    actions: actions.slice(0, 3),
    dataGaps: [...new Set(dataGaps)],
    methodology: 'category-top-items-profile-v1'
  };
}

function parseArgs(argv) {
  const options = { limit: 20 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--input') options.input = argv[++index];
    else if (argv[index] === '--limit') options.limit = Number(argv[++index]);
  }
  if (!options.input) throw new Error('--input is required.');
  if (!Number.isInteger(options.limit) || options.limit < 1 || options.limit > 100) throw new Error('--limit must be an integer from 1 to 100.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    process.stdout.write(`${JSON.stringify(profileTopItems(JSON.parse(fs.readFileSync(options.input, 'utf8')), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'CATEGORY_TOP_ITEMS_PROFILE_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
