import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeItemTraffic } from '../skills/item-traffic-analysis/scripts/analyze.mjs';

const metric = (value, cycleCrc = null) => ({ value, cycleCrc });

test('item traffic analysis aggregates roots without double-counting child channels', () => {
  const result = analyzeItemTraffic({
    itemId: '1',
    dateRange: '2026-10-01|2026-10-07',
    tree: [
      { pageId: metric('a'), pageName: metric('付费'), uv: metric(100, -0.2), payAmt: metric(1000, -0.1), payByrCnt: metric(10), payRate: metric(0.1), children: [{ pageName: metric('关键词'), uv: metric(100), payAmt: metric(1000) }] },
      { pageId: metric('b'), pageName: metric('搜索'), uv: metric(50, 0.2), payAmt: metric(800, 0.3), payByrCnt: metric(15), payRate: metric(0.3) }
    ],
    channels: []
  }, { store: 'demo', overview: { itemId: '1', dateRange: '2026-10-01|2026-10-07', metrics: { itmUv: metric(150), payAmt: metric(1800), payByrCnt: metric(25) } } });
  assert.equal(result.store, 'demo');
  assert.equal(result.treeTotals.uv, 150);
  assert.equal(result.itemTotals.payAmt, 1800);
  assert.equal(result.reconciliation.uvRelativeGap, 0);
  assert.equal(result.rootSources[0].overallUvContribution, 2 / 3);
  assert.equal(result.rootSources.length, 2);
  assert.equal(result.topTraffic[0].name, '付费');
  assert.equal(result.highConversion[0].name, '搜索');
  assert.ok(result.declining.some((row) => row.name === '付费'));
});

test('item traffic analysis preserves missing metrics and excludes tiny samples from efficiency rank', () => {
  const result = analyzeItemTraffic({ tree: [
    { pageName: metric('大渠道'), uv: metric(100), payAmt: metric(null), payRate: metric(0.1) },
    { pageName: metric('成交渠道'), uv: metric(100), payAmt: metric(1000), payRate: metric(0.2) },
    { pageName: metric('小渠道'), uv: metric(1, 10), payAmt: metric(10, 10), payRate: metric(1) }
  ] });
  assert.equal(result.rootSources[0].payAmt, null);
  assert.equal(result.highConversion.some((row) => row.name === '小渠道'), false);
  assert.equal(result.growing.some((row) => row.name === '小渠道'), false);
});

test('item traffic analysis separates mixed signals and withholds overall contribution when totals differ', () => {
  const result = analyzeItemTraffic({ itemId: '1', tree: [
    { pageName: metric('搜索'), uv: metric(100, 0.3), payAmt: metric(500, -0.2), payRate: metric(0.1) }
  ] }, { overview: { itemId: '1', metrics: { itmUv: metric(80), payAmt: metric(300), payByrCnt: metric(10) } } });
  assert.equal(result.growing.length, 0);
  assert.equal(result.declining.length, 0);
  assert.equal(result.mixed[0].name, '搜索');
  assert.deepEqual(result.mixed[0].positiveSignals, ['uv']);
  assert.deepEqual(result.mixed[0].negativeSignals, ['payAmt']);
  assert.equal(result.rootSources[0].overallUvContribution, null);
  assert.ok(result.dataGaps.some((message) => message.includes('do not reconcile')));
});
