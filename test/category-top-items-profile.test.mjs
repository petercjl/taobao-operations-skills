import test from 'node:test';
import assert from 'node:assert/strict';
import { profileTopItems } from '../skills/category-top-items-profile/scripts/analyze.mjs';

const upstream = {
  store: 'demo', categoryId: '10', dateRange: '2026-10-01|2026-10-07', rankType: 'gmv',
  completeness: { requested: 2, completeForRequestedTop: true },
  topItems: [
    { rank: 1, rankComparison: null, itemId: 'a', title: 'A', shopTitle: 'Shop', coreKeywords: ['烘焙', '模具'] },
    { rank: 2, rankComparison: 3, itemId: 'b', title: 'B', shopTitle: 'Shop', coreKeywords: ['烘焙'] }
  ],
  keywordFrequency: [{ keyword: '烘焙', itemCount: 2, itemShare: 1 }],
  shopDistribution: [{ shopTitle: 'Shop', itemCount: 2, itemShare: 1 }],
  dataGaps: ['No exact GMV.']
};

test('Top-item profile preserves upstream rows and platform keyword evidence', () => {
  const result = profileTopItems(upstream, { limit: 2 });
  assert.equal(result.status, 'success');
  assert.equal(result.topItems.length, 2);
  assert.deepEqual(result.positioningKeywords[0], { keyword: '烘焙', itemCount: 2, itemShare: 1 });
  assert.equal(result.recurringShops[0].itemCount, 2);
  assert.deepEqual(result.rankMovementSummary, { positiveComparison: 1, negativeComparison: 0, zeroComparison: 0, unavailable: 1 });
  assert.ok(result.actions.length <= 3);
});

test('Top-item profile propagates partial completeness and rejects contract gaps', () => {
  const partial = profileTopItems({ ...upstream, completeness: { requested: 10, completeForRequestedTop: false } });
  assert.equal(partial.status, 'partial');
  assert.ok(partial.dataGaps.some((message) => message.includes('incomplete')));
  assert.throws(() => profileTopItems({ completeness: {}, topItems: [] }), /CONTRACT_MISMATCH/);
});
