function number(value) { return typeof value === 'number' && Number.isFinite(value) ? value : null; }
function percentile(values, value) { const valid = values.filter((item) => item !== null).sort((a, b) => a - b); if (!valid.length || value === null) return null; return valid.filter((item) => item <= value).length / valid.length; }

export function mineOpportunities(rows, { limit = 20 } = {}) {
  if (!Array.isArray(rows)) throw new Error('CONTRACT_MISMATCH: rows must be an array.');
  const fields = ['demand', 'efficiency', 'competitionGap', 'growth'];
  const vectors = Object.fromEntries(fields.map((field) => [field, rows.map((row) => number(row[field]))]));
  const candidates = rows.map((row) => {
    const signals = Object.fromEntries(fields.map((field) => [field, percentile(vectors[field], number(row[field]))]));
    const present = fields.filter((field) => signals[field] !== null);
    const weights = { demand: 0.35, efficiency: 0.25, competitionGap: 0.25, growth: 0.15 };
    const weightTotal = present.reduce((sum, field) => sum + weights[field], 0);
    const score = weightTotal ? present.reduce((sum, field) => sum + signals[field] * weights[field], 0) / weightTotal : null;
    return { id: row.id || row.keyword || row.categoryId || row.priceBand || null, type: row.type || null, signals, score, evidenceCoverage: present.length / fields.length, evidence: row.evidence || [], counterEvidence: row.counterEvidence || [] };
  }).sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).slice(0, limit).map((row) => ({ ...row, priority: row.evidenceCoverage < 0.75 ? 'observe' : row.score >= 0.75 ? 'high' : row.score >= 0.5 ? 'medium' : 'observe' }));
  return { methodology: { version: 'percentile-v1', weights: { demand: 0.35, efficiency: 0.25, competitionGap: 0.25, growth: 0.15 }, minimumHighCoverage: 0.75 }, candidates, validationPlan: candidates.map((row) => ({ id: row.id, action: '用小规模商品/关键词测试验证需求、转化与毛利，达到预设门槛后再扩大。' })), dataGaps: candidates.filter((row) => row.evidenceCoverage < 1).map((row) => `${row.id || 'unknown'} has incomplete signals.`) };
}
