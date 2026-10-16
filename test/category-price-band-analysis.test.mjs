import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzePriceBands } from '../skills/category-price-band-analysis/scripts/analyze.mjs';

const segments = { store: 'demo', cateId: '10', dateRange: '2026-10-01|2026-10-07', priceSegs: [
  { priceSegId: '1', label: '0-20', minPrice: '0', maxPrice: '20', isOpenEnded: false },
  { priceSegId: '2', label: '20以上', minPrice: '20', maxPrice: '', isOpenEnded: true }
] };

function ranking(priceSeg, title) {
  return { cateId: '10', filters: { priceSeg }, targetTopN: 1, recordCount: 100, fetchedPages: 1, stoppedBy: 'targetTopN', duplicateCount: 0, warnings: [], items: [{ rank: 1, itemId: priceSeg, title, shopTitle: `Shop ${priceSeg}`, payByrCnt: '100 ~ 250', uv: '500 ~ 1000' }] };
}

test('price-band analysis preserves band boundaries and traceable samples', () => {
  const result = analyzePriceBands(segments, [ranking('1', 'Low'), ranking('2', 'High')], { samplePerBand: 1 });
  assert.equal(result.bands.length, 2);
  assert.equal(result.bands[0].label, '0-20');
  assert.equal(result.bands[1].isOpenEnded, true);
  assert.equal(result.bands[0].sampleCompleteness.completeForRequestedSample, true);
  assert.equal(result.bands[0].topItems[0].payBuyerRange, '100 ~ 250');
  assert.ok(result.actions.length <= 3);
});

test('price-band analysis rejects a ranking without a matching applied filter', () => {
  assert.throws(() => analyzePriceBands(segments, [ranking('1', 'Low'), { ...ranking('2', 'High'), filters: { priceSeg: '3' } }]), /PRICE_SEGMENT_TRACE_MISMATCH/);
});
