import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeComprehensiveProduct } from '../skills/comprehensive-product-data-analysis/scripts/analyze.mjs';

const metric = (value, cycleCrc = null) => ({ value, cycleCrc });

test('comprehensive product diagnosis preserves nulls and composes traffic and funnel evidence', () => {
  const result = analyzeComprehensiveProduct({
    store: 'demo',
    overview: { itemId: '1', dateType: 'recent7', dateRange: '2026-10-01|2026-10-07', metrics: { payAmt: metric(1000, -0.2), itmUv: metric(100, 0.2), payByrCnt: metric(10), payRate: metric(null), rfdSucAmt: metric(20) } },
    diagnose: { itemId: '1', dateType: 'recent7', dateRange: '2026-10-01|2026-10-07', metrics: { payAmt: metric(1000), payAmtCrc: metric(-0.2), payAmtItemCmpt: metric(0.1) } },
    detail: { itemId: '1', dateType: 'recent7', dateRange: '2026-10-01|2026-10-07', modules: [{ detailTypeCn: '详情到支付', itemLossRate: metric(0.6), itemLossUv: metric(60), itemPayUv: metric(10) }] },
    traffic: { store: 'demo', itemId: '1', dateRange: '2026-10-01|2026-10-07', treeTotals: { uv: 100 }, itemTotals: { uv: 100 }, reconciliation: { uvRelativeGap: 0 }, topTraffic: [{ name: '搜索', uv: 80 }], topSales: [], highConversion: [], growing: [], declining: [{ name: '广告', uv: 20, uvComparison: -0.3 }], mixed: [], actions: ['广告出现明确下滑信号。'], dataGaps: ['No advertising cost.'] }
  });
  assert.equal(result.store, 'demo');
  assert.equal(result.coreMetrics.payRate.value, null);
  assert.equal(result.funnelStages[0].lossRate, 0.6);
  assert.equal(result.traffic.topTraffic[0].name, '搜索');
  assert.ok(result.risks.some((row) => row.type === 'core-decline'));
  assert.ok(result.risks.some((row) => row.type === 'traffic-decline'));
  assert.ok(result.actions.length <= 3);
});

test('comprehensive product diagnosis rejects cross-item inputs', () => {
  assert.throws(() => analyzeComprehensiveProduct({
    overview: { itemId: '1', metrics: {} },
    diagnose: { itemId: '2', metrics: {} },
    detail: { itemId: '1', modules: [] },
    traffic: null
  }), /itemId differs/);
});
