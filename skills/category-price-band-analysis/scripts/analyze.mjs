#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function numberOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value && typeof value === 'object' && 'value' in value ? value.value : value);
  return Number.isFinite(number) ? number : null;
}

function textOf(value) {
  if (value === null || value === undefined || value === '') return null;
  return String(value);
}

function distribution(items, field) {
  const counts = new Map();
  for (const item of items) {
    const value = textOf(item[field]);
    if (value === null) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()].map(([range, itemCount]) => ({ range, itemCount })).sort((a, b) => b.itemCount - a.itemCount || a.range.localeCompare(b.range, 'zh-CN'));
}

function compactItem(row) {
  return {
    rank: numberOf(row.rank),
    itemId: row.itemId === null || row.itemId === undefined ? null : String(row.itemId),
    title: row.title ?? null,
    shopTitle: row.shopTitle ?? null,
    payBuyerRange: textOf(row.payByrCnt),
    visitorRange: textOf(row.uv),
    searchVisitorRange: textOf(row.searchUv),
    coreKeywords: row.coreKeywords ?? null
  };
}

export function analyzePriceBands(segmentsInput, rankingInputs, { store = null, samplePerBand = 5 } = {}) {
  const segmentData = segmentsInput?.data?.priceSegs ? segmentsInput.data : segmentsInput;
  const segments = Array.isArray(segmentData?.priceSegs) ? segmentData.priceSegs : [];
  if (!segments.length) throw new Error('Price-segment input contains no price bands.');
  const rankings = new Map();
  for (const input of rankingInputs) {
    const data = input?.data?.items ? input.data : input;
    const priceSeg = textOf(data?.filters?.priceSeg);
    if (!priceSeg) throw new Error('PRICE_SEGMENT_TRACE_MISMATCH: ranking input is missing filters.priceSeg.');
    if (rankings.has(priceSeg)) throw new Error(`PRICE_SEGMENT_TRACE_MISMATCH: duplicate ranking input for price segment ${priceSeg}.`);
    rankings.set(priceSeg, data);
  }
  const bands = segments.map((segment) => {
    const priceSegmentId = textOf(segment.priceSegId ?? segment.value);
    const ranking = rankings.get(priceSegmentId);
    if (!ranking) throw new Error(`PRICE_SEGMENT_TRACE_MISMATCH: missing ranking input for price segment ${priceSegmentId}.`);
    if (textOf(ranking.cateId) !== textOf(segmentData.cateId)) throw new Error(`PRICE_SEGMENT_TRACE_MISMATCH: category mismatch for price segment ${priceSegmentId}.`);
    const items = (Array.isArray(ranking.items) ? ranking.items : []).map(compactItem).filter((item) => item.itemId || item.title).slice(0, samplePerBand);
    const warnings = Array.isArray(ranking.warnings) ? ranking.warnings : [];
    const recordCount = numberOf(ranking.recordCount);
    const expected = Math.min(samplePerBand, recordCount ?? samplePerBand);
    const cleanStop = ['targetTopN', 'shortPage', 'emptyPage'].includes(ranking.stoppedBy);
    return {
      priceSegmentId,
      label: segment.label ?? segment.priceSegName ?? null,
      minPrice: textOf(segment.minPrice),
      maxPrice: textOf(segment.maxPrice),
      isOpenEnded: Boolean(segment.isOpenEnded),
      sampleCompleteness: {
        requested: samplePerBand,
        returnedCount: items.length,
        recordCount,
        fetchedPages: numberOf(ranking.fetchedPages),
        stoppedBy: ranking.stoppedBy ?? null,
        duplicateCount: numberOf(ranking.duplicateCount) ?? 0,
        completeForRequestedSample: items.length >= expected && cleanStop && warnings.length === 0,
        warnings
      },
      topItems: items,
      payBuyerRangeDistribution: distribution(items, 'payBuyerRange'),
      visitorRangeDistribution: distribution(items, 'visitorRange'),
      uniqueShopCount: new Set(items.map((item) => item.shopTitle).filter(Boolean)).size
    };
  });
  const incomplete = bands.filter((band) => !band.sampleCompleteness.completeForRequestedSample);
  const actions = [];
  const first = bands[0];
  const middle = bands[Math.floor((bands.length - 1) / 2)];
  const last = bands[bands.length - 1];
  const referenceBands = [...new Map([first, middle, last].filter(Boolean).map((band) => [band.priceSegmentId, band])).values()];
  if (referenceBands.length) actions.push(`先用 ${referenceBands.map((band) => `“${band.label}”`).join('、')} 的第 1 名商品建立低、中、高价位定位对照，再比较标题、店铺与平台返回的买家区间。`);
  const diverse = [...bands].sort((a, b) => b.uniqueShopCount - a.uniqueShopCount)[0];
  if (diverse?.uniqueShopCount) actions.push(`“${diverse.label}”头部 ${diverse.topItems.length} 个样本来自 ${diverse.uniqueShopCount} 家店：用于建立竞品样本池；该店铺数只描述本次头部样本，不代表竞争度或市场份额。`);
  actions.push('把候选售价与自身成本、毛利、库存和店铺转化数据共同验证后再定价；市场排行样本只提供外部定位证据。');
  const dataGaps = [
    'Per-band Top-item samples do not provide total band GMV, market size, market share, profit, or an optimal price.',
    'Buyer and visitor metrics may be platform ranges; ranges are preserved and are not converted into exact totals.'
  ];
  if (incomplete.length) dataGaps.unshift(`Incomplete price-band samples: ${incomplete.map((band) => band.label).join(', ')}.`);
  return {
    store: store ?? segmentsInput.store ?? null,
    categoryId: segmentData.cateId ?? null,
    dateRange: segmentData.dateRange ?? null,
    samplePerBand,
    bands,
    actions: actions.slice(0, 3),
    dataGaps,
    methodology: 'category-price-band-analysis-v1'
  };
}

function parseArgs(argv) {
  const options = { samplePerBand: 5 };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--segments') options.segments = argv[++index];
    else if (argv[index] === '--rankings-dir') options.rankingsDir = argv[++index];
    else if (argv[index] === '--store') options.store = argv[++index];
    else if (argv[index] === '--sample-per-band') options.samplePerBand = Number(argv[++index]);
  }
  if (!options.segments) throw new Error('--segments is required.');
  if (!options.rankingsDir) throw new Error('--rankings-dir is required.');
  if (!Number.isInteger(options.samplePerBand) || options.samplePerBand < 1 || options.samplePerBand > 20) throw new Error('--sample-per-band must be an integer from 1 to 20.');
  return options;
}

if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  try {
    const options = parseArgs(process.argv.slice(2));
    const segments = JSON.parse(fs.readFileSync(options.segments, 'utf8'));
    const rankingFiles = fs.readdirSync(options.rankingsDir).filter((name) => /^rank-[A-Za-z0-9_]+\.json$/u.test(name)).sort();
    const rankings = rankingFiles.map((name) => JSON.parse(fs.readFileSync(path.join(options.rankingsDir, name), 'utf8')));
    process.stdout.write(`${JSON.stringify(analyzePriceBands(segments, rankings, options), null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ ok: false, error: { code: 'CATEGORY_PRICE_BAND_ANALYSIS_FAILED', message: error.message } })}\n`);
    process.exitCode = 1;
  }
}
