import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPerformanceReport } from '../skills/weekly-or-monthly-store-performance-reports/scripts/report.mjs';

test('weekly report preserves missing values and links actions to returned comparisons', () => {
  const report = buildPerformanceReport({
    dateRange: '2026-10-05|2026-10-11',
    metrics: { payAmt: 1000, uv: 100, payBuyerCnt: 8, payRate: 0.08, payPct: null },
    comparisons: { payAmtVariRate: -0.1, uvVariRate: -0.2, payBuyerCntVariRate: -0.1, payRateVariRate: 0.1, payPctVariRate: null }
  }, { periodType: 'weekly', label: '测试周报', store: 'test-shop' });
  assert.equal(report.store, 'test-shop');
  assert.equal(report.metrics.payPct, null);
  assert.ok(report.dataGaps.includes('客单价未返回'));
  assert.match(report.markdown, /访客数：100；变化 -20\.00%/);
  assert.ok(report.actions.some((row) => row.includes('流量入口')));
});

test('monthly report rejects a missing traceable date range', () => {
  assert.throws(() => buildPerformanceReport({ metrics: {} }, { periodType: 'monthly' }), /dateRange/);
});
