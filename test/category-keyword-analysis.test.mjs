import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeCategoryKeywords } from '../skills/category-keyword-analysis/scripts/analyze.mjs';

test('category keyword analysis preserves ranges and reports complete Top N', () => {
  const result = analyzeCategoryKeywords({
    store: 'demo', cateId: '10', dateRange: '2026-10-01|2026-10-07', rankType: 'hot',
    targetTopN: 2, recordCount: 300, returnedCount: 2, fetchedPages: 1, stoppedBy: 'targetTopN', duplicateCount: 0, warnings: [],
    words: [
      { searchWord: '模具', rank: 1, seIpvUvHits: '1万 ~ 2万', seIpvUvHitsCrc: null, clickThroughRate: 0.58, payRate: '10% ~ 15%' },
      { searchWord: '蛋糕模具', rank: 2, seIpvUvHits: '1万 ~ 2万', seIpvUvHitsCrc: 3, clickThroughRate: 0.75, payRate: '15% ~ 20%' }
    ]
  }, { limit: 2 });
  assert.equal(result.completeness.completeForRequestedTop, true);
  assert.equal(result.topKeywords[0].searchVisitorRange, '1万 ~ 2万');
  assert.equal(result.topKeywords[0].payRateRange, '10% ~ 15%');
  assert.equal(result.topKeywords[0].clickThroughRateReturned, 0.58);
  assert.deepEqual(result.trafficBandDistribution[0], { range: '1万 ~ 2万', keywordCount: 2, keywordShare: 1 });
  assert.deepEqual(result.movementSummary, { rising: 1, declining: 0, unchanged: 0, unavailable: 1 });
  assert.ok(result.actions.length <= 3);
});

test('category keyword analysis rejects false completeness and keeps missing metrics', () => {
  const result = analyzeCategoryKeywords({
    targetTopN: 20, recordCount: 300, returnedCount: 20, fetchedPages: 1, stoppedBy: 'maxPages', warnings: ['page limit reached'],
    words: [{ searchWord: '模具', rank: 1, seIpvUvHits: null, payRate: null }]
  });
  assert.equal(result.completeness.completeForRequestedTop, false);
  assert.equal(result.topKeywords[0].searchVisitorRange, null);
  assert.equal(result.topKeywords[0].payRateRange, null);
  assert.ok(result.dataGaps.some((message) => message.includes('incomplete')));
});
