#!/usr/bin/env node
import fs from 'node:fs';

function metric(item, name) {
  const value = item?.metrics?.[name]?.value;
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function comparison(item, name) {
  const value = item?.metrics?.[name]?.cycleCrc;
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function quantile(values, ratio) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const position = (sorted.length - 1) * ratio;
  const low = Math.floor(position);
  const high = Math.ceil(position);
  return low === high ? sorted[low] : sorted[low] + (sorted[high] - sorted[low]) * (position - low);
}

function atLeast(value, threshold) {
  return value !== null && threshold !== null && value >= threshold;
}

function compact(item, reasons) {
  return {
    itemId: item.itemId,
    title: item.title,
    isNew: item.isNew,
    metrics: {
      payAmt: metric(item, 'payAmt'),
      payAmtCycleCrc: comparison(item, 'payAmt'),
      payByrCnt: metric(item, 'payByrCnt'),
      itmUv: metric(item, 'itmUv'),
      payRate: metric(item, 'payRate'),
      payPct: metric(item, 'payPct'),
      itemCartCnt: metric(item, 'itemCartCnt'),
      itemCltByrCnt: metric(item, 'itemCltByrCnt'),
      sucRefundAmt: metric(item, 'sucRefundAmt')
    },
    reasons
  };
}

export function analyzeItemPortfolio(input, { direction = 'both', limit = 20 } = {}) {
  const data = input?.data?.items ? input.data : input;
  const source = Array.isArray(data?.items) ? data.items : [];
  const items = source.filter((item) => item?.itemId && item.online !== false);
  if (!items.length) throw new Error('No shop item rows are available for analysis.');
  const thresholds = {
    payAmtP75: quantile(items.map((item) => metric(item, 'payAmt')), 0.75),
    payAmtP50: quantile(items.map((item) => metric(item, 'payAmt')), 0.5),
    payByrCntP50: quantile(items.map((item) => metric(item, 'payByrCnt')), 0.5),
    itmUvP75: quantile(items.map((item) => metric(item, 'itmUv')), 0.75),
    itmUvP50: quantile(items.map((item) => metric(item, 'itmUv')), 0.5),
    payRateP50: quantile(items.map((item) => metric(item, 'payRate')), 0.5)
  };
  const groups = { core: [], potential: [], traffic: [], observe: [] };
  for (const item of items) {
    const payAmt = metric(item, 'payAmt');
    const buyers = metric(item, 'payByrCnt');
    const uv = metric(item, 'itmUv');
    const rate = metric(item, 'payRate');
    const growth = comparison(item, 'payAmt');
    const isCore = atLeast(payAmt, thresholds.payAmtP75) && atLeast(buyers, thresholds.payByrCntP50);
    const highQualityTraffic = atLeast(uv, thresholds.itmUvP75) && atLeast(rate, thresholds.payRateP50);
    const improvingBase = atLeast(payAmt, thresholds.payAmtP50) && growth !== null && growth > 0 && (atLeast(uv, thresholds.itmUvP50) || atLeast(rate, thresholds.payRateP50));
    const isPotential = !isCore && (highQualityTraffic || improvingBase);
    const isTraffic = !isCore && !isPotential && atLeast(uv, thresholds.itmUvP75);
    if (isCore) groups.core.push(compact(item, ['payAmt>=P75', 'payByrCnt>=P50']));
    else if (isPotential) groups.potential.push(compact(item, [highQualityTraffic ? 'itmUv>=P75 and payRate>=P50' : 'payAmt>=P50 with positive platform comparison and traffic or conversion>=P50']));
    else if (isTraffic) groups.traffic.push(compact(item, ['itmUv>=P75', 'payRate<P50']));
    else groups.observe.push(compact(item, ['below current shop selection thresholds']));
  }
  groups.core.sort((a, b) => (b.metrics.payAmt ?? -Infinity) - (a.metrics.payAmt ?? -Infinity));
  groups.potential.sort((a, b) => (b.metrics.payAmt ?? -Infinity) - (a.metrics.payAmt ?? -Infinity) || (b.metrics.payAmtCycleCrc ?? -Infinity) - (a.metrics.payAmtCycleCrc ?? -Infinity));
  groups.traffic.sort((a, b) => (b.metrics.itmUv ?? -Infinity) - (a.metrics.itmUv ?? -Infinity));
  groups.observe.sort((a, b) => (b.metrics.payAmt ?? -Infinity) - (a.metrics.payAmt ?? -Infinity));
  const selected = direction === 'core' ? ['core'] : direction === 'potential' ? ['potential', 'traffic'] : ['core', 'potential', 'traffic'];
  const outputGroups = Object.fromEntries(selected.map((name) => [name, groups[name].slice(0, limit)]));
  const complete = Number(data.returnedCount) === Number(data.recordCount) && Number(data.recordCount) > 0;
  return {
    direction,
    dateRange: data.dateRange ?? null,
    completeness: { complete, recordCount: data.recordCount ?? null, returnedCount: data.returnedCount ?? items.length, fetchedPages: data.fetchedPages ?? null, stoppedBy: data.stoppedBy ?? null },
    analyzedItemCount: items.length,
    thresholds,
    groupCounts: Object.fromEntries(Object.entries(groups).map(([name, rows]) => [name, rows.length])),
    groups: outputGroups,
    methodology: 'within-shop-distribution-v1',
    warnings: complete ? [] : ['The collected item set is incomplete; potential and traffic classifications may change after a full collection.']
  };
}

function parseArgs(argv) {
  const options = { direction: 'both', limit: 20 };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--input') options.input = argv[++index];
    else if (value === '--direction') options.direction = argv[++index];
    else if (value === '--limit') options.limit = Number(argv[++index]);
  }
  if (!['core', 'potential', 'both'].includes(options.direction)) throw new Error('--direction must be core, potential, or both.');
  if (!Number.isInteger(options.limit) || options.limit < 1 || options.limit > 200) throw new Error('--limit must be an integer from 1 to 200.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const text = options.input ? fs.readFileSync(options.input, 'utf8') : fs.readFileSync(0, 'utf8');
    process.stdout.write(`${JSON.stringify(analyzeItemPortfolio(JSON.parse(text), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'ITEM_PORTFOLIO_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
