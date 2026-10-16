#!/usr/bin/env node
import fs from 'node:fs';

function valueOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const raw = value && typeof value === 'object' && 'value' in value ? value.value : value;
  if (raw === null || raw === undefined || raw === '') return null;
  const number = Number(raw);
  return Number.isFinite(number) ? number : null;
}

function comparisonOf(value) {
  if (!value || typeof value !== 'object') return null;
  return valueOf(value.cycleCrc);
}

function metric(source, key) {
  const raw = source?.[key];
  return { value: valueOf(raw), comparison: comparisonOf(raw) };
}

function diagnostic(source, valueKey, comparisonKey, benchmarkKey, benchmarkComparisonKey) {
  return {
    value: valueOf(source?.[valueKey]),
    periodComparison: valueOf(source?.[comparisonKey]),
    platformComparison: valueOf(source?.[benchmarkKey]),
    platformComparisonChange: valueOf(source?.[benchmarkComparisonKey])
  };
}

function textOf(value) {
  const raw = value && typeof value === 'object' && 'value' in value ? value.value : value;
  return raw === null || raw === undefined || raw === '' ? null : String(raw);
}

function funnelStage(row) {
  return {
    name: textOf(row.detailTypeCn) ?? textOf(row.detailType),
    level: valueOf(row.detailLevel),
    exposeUv: valueOf(row.itemExposeUv),
    interactUv: valueOf(row.itemInteractUv),
    collectUv: valueOf(row.itemCollectUv),
    cartUv: valueOf(row.itemCartUv),
    orderUv: valueOf(row.itemOrderUv),
    payUv: valueOf(row.itemPayUv),
    cartConvertRate: valueOf(row.itemCartConvertRate),
    payConvertRate: valueOf(row.itemPayConvertRate),
    lossUv: valueOf(row.itemLossUv),
    lossRate: valueOf(row.itemLossRate)
  };
}

function ensureObject(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label} must be a JSON object.`);
}

function sameIdentity(values, label) {
  const present = values.filter((value) => value !== null && value !== undefined && value !== '');
  if (new Set(present.map(String)).size > 1) throw new Error(`${label} differs across inputs.`);
  return present.length ? String(present[0]) : null;
}

export function analyzeComprehensiveProduct({ overview, diagnose, detail, traffic, store = null }) {
  ensureObject(overview, 'Overview input');
  ensureObject(diagnose, 'Diagnose input');
  ensureObject(detail, 'Detail input');
  if (traffic !== null && traffic !== undefined) ensureObject(traffic, 'Traffic input');

  const itemId = sameIdentity([overview.itemId, diagnose.itemId, detail.itemId, traffic?.itemId], 'itemId');
  const dateRange = sameIdentity([overview.dateRange, diagnose.dateRange, detail.dateRange, traffic?.dateRange], 'dateRange');
  sameIdentity([overview.dateType, diagnose.dateType, detail.dateType], 'dateType');
  if (traffic?.store && store && traffic.store !== store) throw new Error('store differs across inputs.');

  const metrics = overview.metrics ?? {};
  const diagnosisMetrics = diagnose.metrics ?? {};
  const coreMetrics = {
    payAmt: metric(metrics, 'payAmt'),
    itemUv: metric(metrics, 'itmUv'),
    payBuyerCnt: metric(metrics, 'payByrCnt'),
    payRate: metric(metrics, 'payRate'),
    uvValue: metric(metrics, 'uvAvgValue'),
    refundAmt: metric(metrics, 'rfdSucAmt'),
    bounceRate: metric(metrics, 'itmBounceRate'),
    stayTime: metric(metrics, 'itmStayTime'),
    cartRate: metric(metrics, 'visitCartRate'),
    collectRate: metric(metrics, 'visitCltRate')
  };

  const platformDiagnosis = {
    visitors: diagnostic(diagnosisMetrics, 'uv', 'itemUvCrc', 'itmUvCmpt', 'itmUvCmptCrc'),
    payAmt: diagnostic(diagnosisMetrics, 'payAmt', 'payAmtCrc', 'payAmtItemCmpt', 'payAmtItemCmptCrc'),
    payCount: diagnostic(diagnosisMetrics, 'payCnt', 'payCntCrc', 'payCntCmpt', 'payCntCmptCrc'),
    payRate: diagnostic(diagnosisMetrics, 'payRate', 'payRateCrc', 'payRateCmpt', 'payRateCmptCrc'),
    focusMetric: diagnose.focusMetric ?? null,
    focusDifference: valueOf(diagnose.focusDifference)
  };

  const funnelStages = (Array.isArray(detail.modules) ? detail.modules : []).map(funnelStage).filter((row) => row.name);
  const comparableCore = Object.entries(coreMetrics).filter(([, row]) => row.value !== null && row.comparison !== null);
  const strengths = comparableCore.filter(([, row]) => row.comparison >= 0.1).sort((a, b) => b[1].comparison - a[1].comparison).slice(0, 3).map(([metricName, row]) => ({ type: 'core-growth', metric: metricName, value: row.value, comparison: row.comparison }));
  const risks = comparableCore.filter(([metricName, row]) => !['refundAmt', 'bounceRate'].includes(metricName) && row.comparison <= -0.1).sort((a, b) => a[1].comparison - b[1].comparison).slice(0, 3).map(([metricName, row]) => ({ type: 'core-decline', metric: metricName, value: row.value, comparison: row.comparison }));

  const largestLoss = [...funnelStages].filter((row) => row.lossRate !== null).sort((a, b) => b.lossRate - a.lossRate)[0] ?? null;
  if (largestLoss) risks.push({ type: 'funnel-loss', stage: largestLoss.name, lossRate: largestLoss.lossRate, lossUv: largestLoss.lossUv });
  const trafficImpact = (row) => Math.max(row.treeUvShare ?? 0, row.treePayAmtShare ?? 0);
  const leadingTrafficRisk = traffic ? [...(traffic.mixed ?? []).map((row) => ({ type: 'traffic-mixed', row })), ...(traffic.declining ?? []).map((row) => ({ type: 'traffic-decline', row }))].sort((a, b) => trafficImpact(b.row) - trafficImpact(a.row))[0] : null;
  if (leadingTrafficRisk) risks.push({ type: leadingTrafficRisk.type, source: leadingTrafficRisk.row.name, uv: leadingTrafficRisk.row.uv, uvComparison: leadingTrafficRisk.row.uvComparison, payAmt: leadingTrafficRisk.row.payAmt, payAmtComparison: leadingTrafficRisk.row.payAmtComparison });

  const actions = [];
  const coreRisk = risks.find((row) => row.type === 'core-decline');
  const metricLabels = { payAmt: '支付金额', itemUv: '商品访客数', payBuyerCnt: '支付买家数', payRate: '支付转化率', uvValue: '访客价值', stayTime: '平均停留时长', cartRate: '加购率', collectRate: '收藏率' };
  if (coreRisk) actions.push(`${metricLabels[coreRisk.metric] ?? coreRisk.metric}出现明显下滑：先核对对应页面、价格或承接变化；下周期复查该指标及其平台比较值。`);
  if (largestLoss) actions.push(`${largestLoss.name}是当前可见漏斗中流失率最高的阶段：检查该阶段的页面信息和操作阻力；下周期观察流失人数、流失率与支付人数。`);
  if (traffic?.actions?.[0]) actions.push(traffic.actions[0]);
  if (!actions.length && strengths[0]) actions.push(`${strengths[0].metric}保持明显增长：保留当前有效动作并记录变更；下周期观察增长是否延续。`);

  const dataGaps = [];
  if (!funnelStages.length) dataGaps.push('Detail funnel data is unavailable.');
  if (!traffic) dataGaps.push('Traffic-source analysis is unavailable.');
  if (traffic?.dataGaps) dataGaps.push(...traffic.dataGaps);
  dataGaps.push('Cost, profit, inventory, refund reasons, and causal operation-event evidence are not provided by these reads.');

  return {
    store: store ?? traffic?.store ?? null,
    itemId,
    dateRange,
    coreMetrics,
    platformDiagnosis,
    funnelStages,
    traffic: traffic ? {
      treeTotals: traffic.treeTotals ?? null,
      itemTotals: traffic.itemTotals ?? null,
      reconciliation: traffic.reconciliation ?? null,
      topTraffic: traffic.topTraffic ?? [],
      topSales: traffic.topSales ?? [],
      highConversion: traffic.highConversion ?? [],
      growing: traffic.growing ?? [],
      declining: traffic.declining ?? [],
      mixed: traffic.mixed ?? []
    } : null,
    strengths,
    risks: risks.slice(0, 5),
    actions: actions.slice(0, 3),
    dataGaps: [...new Set(dataGaps)],
    methodology: 'comprehensive-item-diagnosis-v1'
  };
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--overview') options.overview = argv[++index];
    else if (argv[index] === '--diagnose') options.diagnose = argv[++index];
    else if (argv[index] === '--detail') options.detail = argv[++index];
    else if (argv[index] === '--traffic') options.traffic = argv[++index];
    else if (argv[index] === '--store') options.store = argv[++index];
  }
  for (const key of ['overview', 'diagnose', 'detail']) if (!options[key]) throw new Error(`--${key} is required.`);
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const read = (path) => JSON.parse(fs.readFileSync(path, 'utf8'));
    process.stdout.write(`${JSON.stringify(analyzeComprehensiveProduct({ overview: read(options.overview), diagnose: read(options.diagnose), detail: read(options.detail), traffic: options.traffic ? read(options.traffic) : null, store: options.store ?? null }), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'COMPREHENSIVE_PRODUCT_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
