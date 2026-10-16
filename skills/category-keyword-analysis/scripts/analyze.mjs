#!/usr/bin/env node
import fs from 'node:fs';

function numberOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value && typeof value === 'object' && 'value' in value ? value.value : value);
  return Number.isFinite(number) ? number : null;
}

function textOf(value) {
  if (value === null || value === undefined || value === '') return null;
  return String(value);
}

function keywordRow(row) {
  return {
    keyword: textOf(row.searchWord ?? row.keyword),
    rank: numberOf(row.rank),
    rankComparison: numberOf(row.seIpvUvHitsCrc),
    searchVisitorRange: textOf(row.seIpvUvHits),
    clickVisitors: numberOf(row.clickUv),
    clickThroughRateReturned: row.clickThroughRate ?? null,
    payRateRange: textOf(row.payRate)
  };
}

function distribution(rows, field) {
  const counts = new Map();
  for (const row of rows) {
    const value = row[field];
    if (value === null) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([range, keywordCount]) => ({ range, keywordCount, keywordShare: rows.length ? keywordCount / rows.length : null }))
    .sort((a, b) => b.keywordCount - a.keywordCount || a.range.localeCompare(b.range, 'zh-CN'));
}

export function analyzeCategoryKeywords(input, { store = null, limit = 50 } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Keyword-rank input must be a JSON object.');
  const data = input.data?.words ? input.data : input;
  const rows = (Array.isArray(data.words) ? data.words : []).map(keywordRow).filter((row) => row.keyword);
  const requested = numberOf(data.targetTopN) ?? limit;
  const recordCount = numberOf(data.recordCount);
  const warnings = Array.isArray(data.warnings) ? data.warnings : [];
  const stoppedBy = data.stoppedBy ?? null;
  const expectedCount = Math.min(requested, recordCount ?? requested);
  const cleanStop = ['targetTopN', 'shortPage', 'emptyPage'].includes(stoppedBy);
  const topKeywords = [...rows]
    .sort((a, b) => (a.rank ?? Number.MAX_SAFE_INTEGER) - (b.rank ?? Number.MAX_SAFE_INTEGER))
    .slice(0, limit);
  const completeness = {
    requested,
    returnedCount: rows.length,
    recordCount,
    fetchedPages: numberOf(data.fetchedPages),
    stoppedBy,
    duplicateCount: numberOf(data.duplicateCount) ?? 0,
    completeForRequestedTop: rows.length >= expectedCount && cleanStop && warnings.length === 0,
    warnings
  };
  const movementSummary = { rising: 0, declining: 0, unchanged: 0, unavailable: 0 };
  for (const row of rows) {
    if (row.rankComparison === null) movementSummary.unavailable += 1;
    else if (row.rankComparison > 0) movementSummary.rising += 1;
    else if (row.rankComparison < 0) movementSummary.declining += 1;
    else movementSummary.unchanged += 1;
  }
  const trafficBandDistribution = distribution(rows, 'searchVisitorRange');
  const payRateBandDistribution = distribution(rows, 'payRateRange');
  const actions = [];
  if (topKeywords[0]) actions.push(`关键词“${topKeywords[0].keyword}”位列第 ${topKeywords[0].rank ?? 1}：先用于标题与竞品搜索基准，并结合其搜索访客区间和支付转化率区间验证需求。`);
  if (trafficBandDistribution[0]) actions.push(`搜索访客区间“${trafficBandDistribution[0].range}”覆盖 ${trafficBandDistribution[0].keywordCount} 个本次 Top 关键词：按该区间建立词组，再比较支付转化率区间，不把区间换算成精确搜索量。`);
  const mover = topKeywords.find((row) => row.rankComparison !== null && row.rankComparison > 0);
  if (mover) actions.push(`“${mover.keyword}”存在平台返回的正向变化值 ${mover.rankComparison}：下一步读取该词明细与趋势，确认变化周期和绝对规模。`);
  else if (topKeywords.length > 1) actions.push(`比较第 1～${Math.min(5, topKeywords.length)} 名关键词的搜索意图与指标区间，筛选标题研究和竞品下钻样本；当前变化指标缺失时不判断趋势。`);
  const dataGaps = [
    'Search-visitor and pay-rate values may be platform ranges; ranges are preserved and are not converted into exact values.',
    'Keyword rank and returned rates do not by themselves establish competition, profitability, market share, or purchase causality.'
  ];
  if (!completeness.completeForRequestedTop) dataGaps.unshift('The requested Top N keyword collection is incomplete or contains collection warnings.');
  return {
    store: store ?? input.store ?? null,
    categoryId: data.cateId ?? null,
    dateRange: data.dateRange ?? null,
    rankType: data.rankType ?? null,
    completeness,
    topKeywords,
    trafficBandDistribution,
    payRateBandDistribution,
    movementSummary,
    actions: actions.slice(0, 3),
    dataGaps,
    methodology: 'category-keyword-analysis-v1'
  };
}

function parseArgs(argv) {
  const options = { limit: 50 };
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
    process.stdout.write(`${JSON.stringify(analyzeCategoryKeywords(JSON.parse(fs.readFileSync(options.input, 'utf8')), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'CATEGORY_KEYWORD_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
