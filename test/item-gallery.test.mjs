import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeItemGallery } from '../skills/item-gallery-analysis/scripts/analyze.mjs';

const metric = (value, cycleCrc = null) => ({ value, cycleCrc });

test('gallery analysis preserves nulls, checks completeness, and gates tiny conversion samples', () => {
  const result = analyzeItemGallery({ itemId: '1', dateRange: '2026-10-01|2026-10-07', recordCount: 3, materials: [
    { contentId: metric('a'), contentType: metric('gallery'), itemExposeUv: metric(1000), itemPayConvertRate: metric(0.1), itemLossRate: metric(0.6), itemPayUv: metric(100) },
    { contentId: metric('b'), contentType: metric('video'), itemExposeUv: metric(100), itemPayConvertRate: metric(0.3), itemLossRate: metric(0.2), itemPayUv: metric(30) },
    { contentId: metric('c'), contentType: metric('gallery'), itemExposeUv: metric(1), itemPayConvertRate: metric(1), itemLossRate: metric(null), itemPayUv: metric(1) }
  ] }, { store: 'demo', limit: 5 });
  assert.equal(result.store, 'demo');
  assert.equal(result.completeness.complete, true);
  assert.equal(result.materials[2].lossRate, null);
  assert.equal(result.highConversion[0].contentId, 'b');
  assert.equal(result.highConversion.some((row) => row.contentId === 'c'), false);
  assert.equal(result.typeSummary.find((row) => row.contentType === 'gallery').count, 2);
  assert.ok(result.actions.length <= 3);
});

test('gallery analysis reports incomplete material collections', () => {
  const result = analyzeItemGallery({ recordCount: 2, materials: [{ contentId: metric('a'), contentType: metric('gallery'), itemExposeUv: metric(10) }] });
  assert.equal(result.completeness.complete, false);
  assert.ok(result.dataGaps.some((message) => message.includes('incomplete')));
});
