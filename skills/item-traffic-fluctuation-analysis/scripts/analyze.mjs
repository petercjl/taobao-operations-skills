function change(current, previous) {
  if (![current, previous].every((value) => typeof value === 'number' && Number.isFinite(value)) || previous === 0) return null;
  return (current - previous) / Math.abs(previous);
}

export function analyzeTrafficFluctuation(current, previous, { threshold = 0.2, minimumUv = 20 } = {}) {
  if (!current || !previous) throw new Error('CONTRACT_MISMATCH: current and previous inputs are required.');
  if (current.itemId && previous.itemId && String(current.itemId) !== String(previous.itemId)) throw new Error('CONTRACT_MISMATCH: itemId differs.');
  const before = new Map((previous.rootSources || []).map((row) => [row.id || row.name, row]));
  const after = new Map((current.rootSources || []).map((row) => [row.id || row.name, row]));
  const keys = new Set([...before.keys(), ...after.keys()]);
  const channelChanges = [...keys].map((key) => {
    const oldRow = before.get(key) || {};
    const newRow = after.get(key) || {};
    const uvChange = change(newRow.uv, oldRow.uv);
    const payAmtChange = change(newRow.payAmt, oldRow.payAmt);
    const eligible = Math.max(oldRow.uv || 0, newRow.uv || 0) >= minimumUv;
    const directions = [uvChange, payAmtChange].filter((value) => value !== null).map((value) => Math.sign(value));
    return { key, name: newRow.name || oldRow.name || key, currentUv: newRow.uv ?? null, previousUv: oldRow.uv ?? null, uvChange, currentPayAmt: newRow.payAmt ?? null, previousPayAmt: oldRow.payAmt ?? null, payAmtChange, eligible, mixed: directions.includes(1) && directions.includes(-1) };
  });
  const drivers = channelChanges.filter((row) => row.eligible && !row.mixed && [row.uvChange, row.payAmtChange].some((value) => value !== null && Math.abs(value) >= threshold)).sort((a, b) => Math.max(Math.abs(b.uvChange || 0), Math.abs(b.payAmtChange || 0)) - Math.max(Math.abs(a.uvChange || 0), Math.abs(a.payAmtChange || 0))).slice(0, 3);
  return { itemId: current.itemId || previous.itemId || null, currentWindow: current.dateRange || null, comparisonWindow: previous.dateRange || null, channelChanges, drivers, mixedSignals: channelChanges.filter((row) => row.mixed), actions: drivers.map((row) => `复核${row.name}的流量入口、素材与承接页，并在下一同口径周期观察访客和支付金额。`), dataGaps: channelChanges.some((row) => row.uvChange === null || row.payAmtChange === null) ? ['Some channel changes are unavailable because values are missing or the comparison value is zero.'] : [] };
}
