import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeItemPortfolio } from '../skills/shop-core-potential-item-analysis/scripts/analyze.mjs';

function item(id, { payAmt, buyers, uv, rate, growth = 0, isNew = false }) {
  const field = (value, cycleCrc = null) => ({ value, cycleCrc, syncCrc: null });
  return { itemId: id, title: `商品${id}`, online: true, isNew, metrics: { payAmt: field(payAmt, growth), payByrCnt: field(buyers), itmUv: field(uv), payRate: field(rate), payPct: field(10), itemCartCnt: field(1), itemCltByrCnt: field(1), sucRefundAmt: field(0) } };
}

test('portfolio analysis classifies shop items from within-shop thresholds', () => {
  const items = [
    item('a', { payAmt: 1000, buyers: 100, uv: 1000, rate: 0.1 }),
    item('b', { payAmt: 800, buyers: 80, uv: 800, rate: 0.12 }),
    item('c', { payAmt: 300, buyers: 30, uv: 900, rate: 0.2, growth: 0.5 }),
    item('d', { payAmt: 100, buyers: 10, uv: 950, rate: 0.01 }),
    item('e', { payAmt: 50, buyers: 5, uv: 100, rate: 0.03 })
  ];
  const result = analyzeItemPortfolio({ dateRange: '2026-10-01|2026-10-07', recordCount: 5, returnedCount: 5, items });
  assert.equal(result.completeness.complete, true);
  assert.ok(result.groupCounts.core >= 1);
  assert.ok(result.groupCounts.potential >= 1);
  assert.ok(result.groupCounts.traffic >= 1);
  assert.equal(result.methodology, 'within-shop-distribution-v1');
});

test('portfolio analysis warns when the item collection is incomplete', () => {
  const result = analyzeItemPortfolio({ recordCount: 10, returnedCount: 1, items: [item('a', { payAmt: 10, buyers: 1, uv: 10, rate: 0.1 })] }, { direction: 'core' });
  assert.equal(result.completeness.complete, false);
  assert.equal(result.warnings.length, 1);
  assert.deepEqual(Object.keys(result.groups), ['core']);
});

test('portfolio analysis preserves explicit missing metric and comparison values', () => {
  const result = analyzeItemPortfolio({
    recordCount: 1,
    returnedCount: 1,
    items: [{
      itemId: 'missing',
      online: true,
      metrics: {
        payAmt: { value: null, cycleCrc: null },
        payByrCnt: { value: 1 },
        itmUv: { value: 1 },
        payRate: { value: 0.1 }
      }
    }]
  });
  assert.equal(result.groups.potential[0].metrics.payAmt, null);
  assert.equal(result.groups.potential[0].metrics.payAmtCycleCrc, null);
});

test('potential output prioritizes proven sales base before low-base growth spikes', () => {
  const items = [
    item('core', { payAmt: 1000, buyers: 100, uv: 1000, rate: 0.2 }),
    item('core2', { payAmt: 500, buyers: 50, uv: 950, rate: 0.18 }),
    item('proven', { payAmt: 400, buyers: 30, uv: 900, rate: 0.15, growth: 0.2 }),
    item('spike', { payAmt: 100, buyers: 5, uv: 500, rate: 0.12, growth: 2 }),
    item('base', { payAmt: 20, buyers: 2, uv: 20, rate: 0.02 }),
    item('base2', { payAmt: 10, buyers: 1, uv: 10, rate: 0.01 }),
    item('base3', { payAmt: 5, buyers: 1, uv: 5, rate: 0.01 })
  ];
  const result = analyzeItemPortfolio({ recordCount: 7, returnedCount: 7, items });
  assert.ok(result.groups.potential.some((row) => row.itemId === 'spike'));
  assert.equal(result.groups.potential[0].itemId, 'proven');
});
