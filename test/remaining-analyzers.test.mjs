import test from 'node:test';
import assert from 'node:assert/strict';
import { profileTopShops } from '../skills/category-top-shops-profile/scripts/analyze.mjs';
import { analyzeTrafficFluctuation } from '../skills/item-traffic-fluctuation-analysis/scripts/analyze.mjs';
import { analyzeEventImpact } from '../skills/item-ops-event-impact-analysis/scripts/analyze.mjs';
import { mineOpportunities } from '../skills/market-blue-ocean-opportunity-mining/scripts/analyze.mjs';

test('shop profile aggregates exact shop names and labels incomplete scope', () => {
  const result = profileTopShops({ cateId: '1', topItems: [
    { itemId: 'a', rank: 1, shopTitle: '甲店', coreKeywords: ['烘焙'] },
    { itemId: 'b', rank: 2, shopTitle: '甲店', coreKeywords: ['模具'] },
    { itemId: 'c', rank: 3, shopTitle: '乙店', coreKeywords: [] }
  ], completeness: { completeForRequestedTop: false } });
  assert.equal(result.topShops[0].shopTitle, '甲店');
  assert.equal(result.topShops[0].itemShare, 2 / 3);
  assert.equal(result.concentration.scope, 'retrieved-sample');
});

test('traffic fluctuation gates tiny samples and separates mixed signals', () => {
  const previous = { itemId: '1', dateRange: 'old', rootSources: [{ name: '搜索', uv: 100, payAmt: 100 }, { name: '小渠道', uv: 1, payAmt: 1 }] };
  const current = { itemId: '1', dateRange: 'new', rootSources: [{ name: '搜索', uv: 150, payAmt: 50 }, { name: '小渠道', uv: 5, payAmt: 10 }] };
  const result = analyzeTrafficFluctuation(current, previous);
  assert.equal(result.drivers.some((row) => row.name === '小渠道'), false);
  assert.equal(result.mixedSignals[0].name, '搜索');
});

test('event impact stays low confidence without a control item', () => {
  const pre = { itemId: '1', dateRange: 'old', coreMetrics: { payAmt: { value: 100 }, itmUv: { value: 50 } } };
  const post = { itemId: '1', dateRange: 'new', coreMetrics: { payAmt: { value: 120 }, itmUv: { value: 60 } } };
  const result = analyzeEventImpact(pre, post, { event: { eventAt: '2026-10-01', eventType: 'image-change' } });
  assert.equal(result.confidence, 'low');
  assert.equal(result.impactAssessment, 'before-after-association');
});

test('blue-ocean score lowers priority when evidence coverage is incomplete', () => {
  const result = mineOpportunities([
    { id: 'a', demand: 100, efficiency: 10, competitionGap: 8, growth: 3 },
    { id: 'b', demand: 80, efficiency: null, competitionGap: 9, growth: null }
  ]);
  assert.equal(result.candidates.find((row) => row.id === 'b').priority, 'observe');
  assert.ok(result.dataGaps.length >= 1);
});
