import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeBestSellingItems } from '../skills/category-best-selling-items-analysis/scripts/analyze.mjs';

test('best-selling analysis preserves ranking evidence and computes descriptive aggregates', () => {
  const result = analyzeBestSellingItems({ cateId: '10', dateRange: '2026-10-01|2026-10-07', rankType: 'gmv', targetTopN: 2, recordCount: 100, returnedCount: 2, fetchedPages: 1, stoppedBy: 'targetTopN', duplicateCount: 0, items: [
    { rank: 2, itemId: 'b', title: 'B', shopTitle: 'Shop', payByrCnt: '10', uv: '100', coreKeywords: '烘焙,模具' },
    { rank: 1, itemId: 'a', title: 'A', shopTitle: 'Shop', payByrCnt: '20', uv: '100', coreKeywords: '烘焙,家用' }
  ] }, { store: 'demo', limit: 2 });
  assert.equal(result.completeness.completeForRequestedTop, true);
  assert.equal(result.topItems[0].itemId, 'a');
  assert.equal(result.topItems[0].buyerVisitorRatio, 0.2);
  assert.deepEqual(result.keywordFrequency[0], { keyword: '烘焙', itemCount: 2, itemShare: 1 });
  assert.equal(result.shopDistribution[0].itemCount, 2);
});

test('best-selling analysis reports incomplete Top N and preserves missing ratios', () => {
  const result = analyzeBestSellingItems({ targetTopN: 10, recordCount: 100, items: [{ rank: 1, itemId: 'a', uv: null, payByrCnt: '2' }] });
  assert.equal(result.completeness.completeForRequestedTop, false);
  assert.equal(result.topItems[0].buyerVisitorRatio, null);
  assert.ok(result.dataGaps.some((message) => message.includes('incomplete')));
});

test('best-selling analysis does not call a warned or ambiguous collection complete', () => {
  const result = analyzeBestSellingItems({
    targetTopN: 2,
    recordCount: 100,
    returnedCount: 2,
    fetchedPages: 1,
    stoppedBy: 'maxPages',
    warnings: ['collection stopped before a verified Top N boundary'],
    items: [{ rank: 1, itemId: 'a' }, { rank: 2, itemId: 'b' }]
  });
  assert.equal(result.completeness.completeForRequestedTop, false);
  assert.ok(result.dataGaps.some((message) => message.includes('incomplete')));
});
