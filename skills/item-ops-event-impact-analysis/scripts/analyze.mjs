function metricValue(source, key) { const value = source?.coreMetrics?.[key]?.value ?? source?.metrics?.[key]?.value ?? source?.metrics?.[key] ?? null; return typeof value === 'number' && Number.isFinite(value) ? value : null; }
function relative(after, before) { return after === null || before === null || before === 0 ? null : (after - before) / Math.abs(before); }

export function analyzeEventImpact(pre, post, { event, controlPre = null, controlPost = null } = {}) {
  if (!pre || !post || !event?.eventAt) throw new Error('CONTRACT_MISMATCH: pre, post, and event.eventAt are required.');
  const preId = pre.itemId || pre.overview?.itemId; const postId = post.itemId || post.overview?.itemId;
  if (preId && postId && String(preId) !== String(postId)) throw new Error('CONTRACT_MISMATCH: itemId differs.');
  const keys = ['payAmt', 'itmUv', 'payByrCnt', 'payRate', 'sucRefundAmt'];
  const metricChanges = keys.map((key) => { const before = metricValue(pre, key); const after = metricValue(post, key); return { metric: key, before, after, relativeChange: relative(after, before) }; });
  let controlComparison = null;
  if (controlPre && controlPost) {
    controlComparison = metricChanges.map((row) => { const controlBefore = metricValue(controlPre, row.metric); const controlAfter = metricValue(controlPost, row.metric); const controlChange = relative(controlAfter, controlBefore); return { metric: row.metric, treatedChange: row.relativeChange, controlChange, difference: row.relativeChange === null || controlChange === null ? null : row.relativeChange - controlChange }; });
  }
  const usable = (controlComparison || metricChanges).filter((row) => (row.difference ?? row.relativeChange) !== null);
  return { event, itemId: preId || postId || null, preWindow: pre.dateRange || null, postWindow: post.dateRange || null, metricChanges, controlComparison, confounders: [], impactAssessment: usable.length ? (controlComparison ? 'controlled-association' : 'before-after-association') : 'insufficient-data', confidence: controlComparison && usable.length >= 3 ? 'medium' : 'low', actions: ['在下一等长周期继续观察相同指标，并记录同期活动、价格、库存和投放变化。'], dataGaps: controlComparison ? [] : ['No control item was supplied; the result does not establish causality.'] };
}
