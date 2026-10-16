#!/usr/bin/env node
import fs from 'node:fs';

function valueOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const raw = value && typeof value === 'object' && 'value' in value ? value.value : value;
  if (raw === null || raw === undefined || raw === '') return null;
  const number = Number(raw);
  return Number.isFinite(number) ? number : null;
}

function textOf(value) {
  const raw = value && typeof value === 'object' && 'value' in value ? value.value : value;
  return raw === null || raw === undefined ? null : String(raw);
}

function comparisonOf(value) {
  if (!value || typeof value !== 'object' || value.cycleCrc === null || value.cycleCrc === undefined || value.cycleCrc === '') return null;
  const number = Number(value.cycleCrc);
  return Number.isFinite(number) ? number : null;
}

function compact(row) {
  return {
    pageId: textOf(row.pageId),
    name: textOf(row.pageName),
    uv: valueOf(row.uv),
    uvComparison: comparisonOf(row.uv),
    pv: valueOf(row.pv),
    payAmt: valueOf(row.payAmt),
    payAmtComparison: comparisonOf(row.payAmt),
    payByrCnt: valueOf(row.payByrCnt),
    payRate: valueOf(row.payRate),
    payRateComparison: comparisonOf(row.payRate)
  };
}

function sum(rows, key) {
  return rows.reduce((total, row) => total + (row[key] ?? 0), 0);
}

function relativeGap(channelTotal, itemTotal) {
  if (channelTotal === null || itemTotal === null || !itemTotal) return null;
  return (channelTotal - itemTotal) / itemTotal;
}

export function analyzeItemTraffic(input, { limit = 10, overview = null, store = null } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Flow input must be a JSON object.');
  const flow = input.data?.tree ? input.data : input;
  const itemOverview = overview?.data?.metrics ? overview.data : overview;
  const roots = Array.isArray(flow.tree) ? flow.tree.map(compact).filter((row) => row.name) : [];
  if (!roots.length) throw new Error('No root traffic-source rows are available.');
  const treeTotals = { uv: sum(roots, 'uv'), payAmt: sum(roots, 'payAmt'), payByrCnt: sum(roots, 'payByrCnt') };
  const itemTotals = itemOverview ? {
    uv: valueOf(itemOverview.metrics?.itmUv),
    payAmt: valueOf(itemOverview.metrics?.payAmt),
    payByrCnt: valueOf(itemOverview.metrics?.payByrCnt)
  } : null;
  const reconciliation = itemTotals ? {
    uvRelativeGap: relativeGap(treeTotals.uv, itemTotals.uv),
    payAmtRelativeGap: relativeGap(treeTotals.payAmt, itemTotals.payAmt),
    payByrCntRelativeGap: relativeGap(treeTotals.payByrCnt, itemTotals.payByrCnt)
  } : null;
  const uvReconcilable = Boolean(reconciliation && reconciliation.uvRelativeGap !== null && Math.abs(reconciliation.uvRelativeGap) <= 0.02);
  const payAmtReconcilable = Boolean(reconciliation && reconciliation.payAmtRelativeGap !== null && Math.abs(reconciliation.payAmtRelativeGap) <= 0.02);
  const rootSources = roots.map((row) => ({
    ...row,
    treeUvShare: row.uv === null || !treeTotals.uv ? null : row.uv / treeTotals.uv,
    treePayAmtShare: row.payAmt === null || !treeTotals.payAmt ? null : row.payAmt / treeTotals.payAmt,
    overallUvContribution: uvReconcilable && row.uv !== null && itemTotals.uv ? row.uv / itemTotals.uv : null,
    overallPayAmtContribution: payAmtReconcilable && row.payAmt !== null && itemTotals.payAmt ? row.payAmt / itemTotals.payAmt : null
  }));
  const by = (key) => [...rootSources].filter((row) => row[key] !== null).sort((a, b) => b[key] - a[key]).slice(0, limit);
  const minimumEfficiencySample = Math.max(10, treeTotals.uv * 0.01);
  const highConversion = [...rootSources].filter((row) => row.payRate !== null && (row.uv ?? 0) >= minimumEfficiencySample).sort((a, b) => b.payRate - a.payRate).slice(0, limit);
  const hasDecisionWeight = (row) => (row.uv ?? 0) >= minimumEfficiencySample || (row.treePayAmtShare ?? 0) >= 0.01;
  const impact = (row) => Math.max(row.treeUvShare ?? 0, row.treePayAmtShare ?? 0);
  const signaled = rootSources.filter(hasDecisionWeight).map((row) => {
    const positiveSignals = [];
    const negativeSignals = [];
    if (row.uvComparison !== null && row.uvComparison >= 0.1) positiveSignals.push('uv');
    if (row.payAmtComparison !== null && row.payAmtComparison >= 0.1) positiveSignals.push('payAmt');
    if (row.uvComparison !== null && row.uvComparison <= -0.1) negativeSignals.push('uv');
    if (row.payAmtComparison !== null && row.payAmtComparison <= -0.1) negativeSignals.push('payAmt');
    return { ...row, positiveSignals, negativeSignals };
  });
  const growing = signaled.filter((row) => row.positiveSignals.length && !row.negativeSignals.length).sort((a, b) => impact(b) - impact(a)).slice(0, limit);
  const declining = signaled.filter((row) => row.negativeSignals.length && !row.positiveSignals.length).sort((a, b) => impact(b) - impact(a)).slice(0, limit);
  const mixed = signaled.filter((row) => row.positiveSignals.length && row.negativeSignals.length).sort((a, b) => impact(b) - impact(a)).slice(0, limit);
  const actions = [];
  const leadingRisk = [...mixed.map((row) => ({ kind: 'mixed', row })), ...declining.map((row) => ({ kind: 'declining', row }))].sort((a, b) => impact(b.row) - impact(a.row))[0];
  if (leadingRisk?.kind === 'mixed') actions.push(`${leadingRisk.row.name}的访客与成交变化信号背离：分别核对入口流量质量和商品承接；下周期同时观察访客数、支付金额与转化率。`);
  else if (leadingRisk?.kind === 'declining') actions.push(`${leadingRisk.row.name}出现明确下滑信号：复核该渠道近期入口、素材或投放变化；下周期观察访客数与支付金额。`);
  if (highConversion[0] && highConversion[0].treeUvShare !== null && highConversion[0].treeUvShare < 0.2) actions.push(`${highConversion[0].name}在有效样本下转化率较高但渠道树内流量占比较低：小步测试增量流量；观察支付转化率是否保持。`);
  if (by('uv')[0] && actions.length < 3) actions.push(`${by('uv')[0].name}是渠道树内主要流量来源：优先稳定其承接链路；观察访客规模、支付金额与转化率。`);
  const dataGaps = ['Traffic-source data alone does not prove channel causality or provide advertising cost and profit.'];
  if (!itemOverview) dataGaps.push('Item overview totals were not supplied, so channel-tree totals could not be reconciled to overall item totals.');
  if (reconciliation && (!uvReconcilable || !payAmtReconcilable)) dataGaps.push('Channel-tree totals do not reconcile to item overview totals; tree shares describe only the returned channel tree and are not overall item contribution rates.');
  return {
    store,
    itemId: flow.itemId ?? itemOverview?.itemId ?? null,
    dateRange: flow.dateRange ?? itemOverview?.dateRange ?? null,
    treeTotals,
    itemTotals,
    reconciliation,
    minimumEfficiencySample,
    rootSources,
    topTraffic: by('uv'),
    topSales: by('payAmt'),
    highConversion,
    growing,
    declining,
    mixed,
    actions: actions.slice(0, 3),
    dataGaps,
    methodology: 'root-channel-tree-distribution-v2'
  };
}

function parseArgs(argv) {
  const options = { limit: 10 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--input') options.input = argv[++index];
    else if (argv[index] === '--overview') options.overviewPath = argv[++index];
    else if (argv[index] === '--store') options.store = argv[++index];
    else if (argv[index] === '--limit') options.limit = Number(argv[++index]);
  }
  if (!Number.isInteger(options.limit) || options.limit < 1 || options.limit > 50) throw new Error('--limit must be an integer from 1 to 50.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const text = options.input ? fs.readFileSync(options.input, 'utf8') : fs.readFileSync(0, 'utf8');
    const overview = options.overviewPath ? JSON.parse(fs.readFileSync(options.overviewPath, 'utf8')) : null;
    process.stdout.write(`${JSON.stringify(analyzeItemTraffic(JSON.parse(text), { ...options, overview }), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'ITEM_TRAFFIC_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
