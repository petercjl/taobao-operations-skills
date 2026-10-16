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
  return raw === null || raw === undefined || raw === '' ? null : String(raw);
}

function comparisonOf(value) {
  return value && typeof value === 'object' ? valueOf(value.cycleCrc) : null;
}

function compact(row, index) {
  const contentId = textOf(row.contentId);
  const contentType = textOf(row.contentType);
  return {
    materialKey: contentId ?? `${contentType ?? 'material'}-row-${index + 1}`,
    positionInResult: index + 1,
    contentId,
    contentType,
    contentInfo: textOf(row.contentInfo),
    exposeUv: valueOf(row.itemExposeUv),
    exposeComparison: comparisonOf(row.itemExposeUv),
    interactUv: valueOf(row.itemInteractUv),
    interactComparison: comparisonOf(row.itemInteractUv),
    cartUv: valueOf(row.itemCartUv),
    collectUv: valueOf(row.itemCollectUv),
    orderUv: valueOf(row.itemOrderUv),
    payUv: valueOf(row.itemPayUv),
    payComparison: comparisonOf(row.itemPayUv),
    payConvertRate: valueOf(row.itemPayConvertRate),
    payConvertComparison: comparisonOf(row.itemPayConvertRate),
    lossUv: valueOf(row.itemLossUv),
    lossRate: valueOf(row.itemLossRate),
    lossComparison: comparisonOf(row.itemLossRate)
  };
}

function sortBy(rows, key, descending = true) {
  return [...rows].filter((row) => row[key] !== null).sort((a, b) => descending ? b[key] - a[key] : a[key] - b[key]);
}

export function analyzeItemGallery(input, { store = null, limit = 5 } = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Gallery input must be a JSON object.');
  const data = input.data?.materials ? input.data : input;
  const materials = (Array.isArray(data.materials) ? data.materials : []).map(compact).filter((row) => row.contentId || row.contentInfo);
  const recordCount = valueOf(data.recordCount);
  const completeness = {
    recordCount,
    returnedCount: materials.length,
    complete: recordCount === null ? null : materials.length >= recordCount
  };
  const maxExposure = Math.max(0, ...materials.map((row) => row.exposeUv ?? 0));
  const minimumConversionSample = Math.max(20, maxExposure * 0.05);
  const topExposure = sortBy(materials, 'exposeUv').slice(0, limit);
  const highConversion = sortBy(materials.filter((row) => (row.exposeUv ?? 0) >= minimumConversionSample), 'payConvertRate').slice(0, limit);
  const highLoss = sortBy(materials.filter((row) => (row.exposeUv ?? 0) >= minimumConversionSample), 'lossRate').slice(0, limit);
  const typeSummary = [...new Set(materials.map((row) => row.contentType ?? 'unknown'))].map((contentType) => ({ contentType, count: materials.filter((row) => (row.contentType ?? 'unknown') === contentType).length }));
  const actions = [];
  const exposureLeader = topExposure[0];
  const lossLeader = highLoss[0];
  const conversionLeader = highConversion[0];
  if (lossLeader && lossLeader.lossRate !== null && lossLeader.lossRate >= 0.5) actions.push(`素材 ${lossLeader.materialKey} 在有效样本下流失率最高：优先检查其承接信息并设置对照测试；下周期观察流失率、支付转化率与支付人数。`);
  if (conversionLeader && exposureLeader && conversionLeader.materialKey !== exposureLeader.materialKey && (conversionLeader.exposeUv ?? 0) < (exposureLeader.exposeUv ?? 0) * 0.5) actions.push(`素材 ${conversionLeader.materialKey} 的支付转化率较高但曝光明显低于头部素材：增加可控测试曝光；观察转化率在更大样本下是否保持。`);
  if (exposureLeader && actions.length < 3) actions.push(`素材 ${exposureLeader.materialKey} 当前曝光最高：保持其稳定曝光并持续监控支付转化率和流失率。`);
  const dataGaps = ['Material rows may share the same visitors, so row metrics are not additive product totals.', 'Performance data does not describe the visual content, position, experiment group, traffic source, cost, or causal reason.'];
  if (completeness.complete === false) dataGaps.unshift('The material collection is incomplete; rankings cover only returned rows.');
  return {
    store: store ?? input.store ?? null,
    itemId: data.itemId ?? null,
    dateRange: data.dateRange ?? null,
    completeness,
    minimumConversionSample,
    typeSummary,
    materials,
    topExposure,
    highConversion,
    highLoss,
    actions: actions.slice(0, 3),
    dataGaps,
    methodology: 'item-gallery-performance-v1'
  };
}

function parseArgs(argv) {
  const options = { limit: 5 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--input') options.input = argv[++index];
    else if (argv[index] === '--store') options.store = argv[++index];
    else if (argv[index] === '--limit') options.limit = Number(argv[++index]);
  }
  if (!options.input) throw new Error('--input is required.');
  if (!Number.isInteger(options.limit) || options.limit < 1 || options.limit > 20) throw new Error('--limit must be an integer from 1 to 20.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    process.stdout.write(`${JSON.stringify(analyzeItemGallery(JSON.parse(fs.readFileSync(options.input, 'utf8')), options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'ITEM_GALLERY_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
