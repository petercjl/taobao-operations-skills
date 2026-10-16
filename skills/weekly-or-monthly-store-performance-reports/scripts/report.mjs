#!/usr/bin/env node
import fs from 'node:fs';

const METRICS = [
  ['payAmt', '销售额', 'currency', 'payAmtVariRate'],
  ['uv', '访客数', 'number', 'uvVariRate'],
  ['payBuyerCnt', '支付买家数', 'number', 'payBuyerCntVariRate'],
  ['payRate', '支付转化率', 'percent', 'payRateVariRate'],
  ['payPct', '客单价', 'currency', 'payPctVariRate']
];

function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function format(value, type) {
  if (value === null) return '平台未返回';
  if (type === 'currency') return `¥${value.toFixed(2)}`;
  if (type === 'percent') return `${(value * 100).toFixed(2)}%`;
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value);
}

function formatChange(value) {
  if (value === null) return '平台未返回';
  const sign = value > 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
}

function driver(name, rate) {
  if (rate === null) return null;
  if (rate >= 0.05) return `${name}增长 ${formatChange(rate)}`;
  if (rate <= -0.05) return `${name}下降 ${formatChange(rate)}`;
  return `${name}基本稳定（${formatChange(rate)}）`;
}

export function buildPerformanceReport(input, { periodType = 'weekly', label, store = null } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Summary input must be a JSON object.');
  if (!['weekly', 'monthly'].includes(periodType)) throw new Error('--period-type must be weekly or monthly.');
  const dateRange = typeof input.dateRange === 'string' ? input.dateRange : null;
  if (!dateRange || !/^\d{4}-\d{2}-\d{2}\|\d{4}-\d{2}-\d{2}$/.test(dateRange)) throw new Error('Summary input must contain dateRange as START|END.');
  const metrics = Object.fromEntries(METRICS.map(([key]) => [key, numberOrNull(input.metrics?.[key])]));
  const comparisons = Object.fromEntries(METRICS.map(([, , , comparisonKey]) => [comparisonKey, numberOrNull(input.comparisons?.[comparisonKey])]));
  const dataGaps = [];
  for (const [key, name, , comparisonKey] of METRICS) {
    if (metrics[key] === null) dataGaps.push(`${name}未返回`);
    if (comparisons[comparisonKey] === null) dataGaps.push(`${name}变化率未返回`);
  }
  const drivers = [
    driver('流量', comparisons.uvVariRate),
    driver('支付转化率', comparisons.payRateVariRate),
    driver('客单价', comparisons.payPctVariRate)
  ].filter(Boolean);
  const risks = [];
  for (const [, name, , comparisonKey] of METRICS) {
    const rate = comparisons[comparisonKey];
    if (rate !== null && rate <= -0.1) risks.push(`${name}较对比周期下降 ${formatChange(rate)}`);
  }
  const actions = [];
  if (comparisons.uvVariRate !== null && comparisons.uvVariRate < 0) actions.push(`访客数变化 ${formatChange(comparisons.uvVariRate)}：复核流量入口与活动承接；下周期观察访客数是否恢复。`);
  if (comparisons.payRateVariRate !== null && comparisons.payRateVariRate < 0) actions.push(`支付转化率变化 ${formatChange(comparisons.payRateVariRate)}：检查高流量页面的购买阻力；下周期观察支付转化率。`);
  if (comparisons.payPctVariRate !== null && comparisons.payPctVariRate < 0) actions.push(`客单价变化 ${formatChange(comparisons.payPctVariRate)}：检查商品组合与优惠结构；下周期观察客单价。`);
  if (comparisons.payAmtVariRate !== null && comparisons.payAmtVariRate > 0 && actions.length < 3) actions.push(`销售额变化 ${formatChange(comparisons.payAmtVariRate)}：保留并记录本周期有效经营动作；下周期验证销售额增长是否延续。`);
  if (!actions.length) actions.push('维持当前经营节奏并记录关键动作；下周期复核销售额、访客数和支付转化率。');
  const reportLabel = label || (periodType === 'weekly' ? '店铺经营周报' : '店铺经营月报');
  const metricLines = METRICS.map(([key, name, type, comparisonKey]) => `- ${name}：${format(metrics[key], type)}；变化 ${formatChange(comparisons[comparisonKey])}`);
  const markdown = [
    `# ${reportLabel}`,
    '',
    `周期：${dateRange.replace('|', ' 至 ')}`,
    '',
    '## 核心指标',
    '',
    ...metricLines,
    '',
    '## 经营判断',
    '',
    ...(drivers.length ? drivers.map((row) => `- ${row}`) : ['- 平台未返回足够的变化率，暂不判断增长驱动。']),
    '',
    '## 风险与机会',
    '',
    ...(risks.length ? risks.map((row) => `- ${row}`) : ['- 当前核心变化率中未发现超过 10% 的下滑项。']),
    '',
    '## 下周期行动',
    '',
    ...actions.slice(0, 3).map((row) => `- ${row}`),
    '',
    '## 数据缺口',
    '',
    ...(dataGaps.length ? dataGaps.map((row) => `- ${row}`) : ['- 本报告所需核心概览字段均已返回。'])
  ].join('\n');
  return { store, dateRange, periodType, metrics, comparisons, drivers, risks, actions: actions.slice(0, 3), dataGaps, markdown };
}

function parseArgs(argv) {
  const options = { periodType: 'weekly' };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--input') options.input = argv[++index];
    else if (value === '--period-type') options.periodType = argv[++index];
    else if (value === '--label') options.label = argv[++index];
    else if (value === '--store') options.store = argv[++index];
  }
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const text = options.input ? fs.readFileSync(options.input, 'utf8') : fs.readFileSync(0, 'utf8');
    process.stdout.write(`${JSON.stringify(buildPerformanceReport(JSON.parse(text), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'PERFORMANCE_REPORT_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
