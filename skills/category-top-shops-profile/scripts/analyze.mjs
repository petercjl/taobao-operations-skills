function finite(value) { return typeof value === 'number' && Number.isFinite(value) ? value : null; }

export function profileTopShops(input, { comparison = null, limit = 20 } = {}) {
  if (!input || !Array.isArray(input.topItems)) throw new Error('CONTRACT_MISMATCH: topItems is required.');
  const rows = new Map();
  for (const item of input.topItems) {
    const shop = String(item.shopTitle || '').trim();
    if (!shop) continue;
    const row = rows.get(shop) || { shopTitle: shop, itemCount: 0, ranks: [], itemIds: [], keywords: new Map() };
    row.itemCount += 1;
    if (finite(item.rank) !== null) row.ranks.push(item.rank);
    if (item.itemId) row.itemIds.push(String(item.itemId));
    for (const keyword of item.coreKeywords || []) row.keywords.set(keyword, (row.keywords.get(keyword) || 0) + 1);
    rows.set(shop, row);
  }
  const denominator = input.topItems.filter((item) => item.shopTitle).length;
  const topShops = [...rows.values()].map((row) => ({
    shopTitle: row.shopTitle,
    itemCount: row.itemCount,
    itemShare: denominator ? row.itemCount / denominator : null,
    bestRank: row.ranks.length ? Math.min(...row.ranks) : null,
    itemIds: row.itemIds,
    coreKeywords: [...row.keywords.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([keyword, itemCount]) => ({ keyword, itemCount }))
  })).sort((a, b) => b.itemCount - a.itemCount || (a.bestRank ?? Infinity) - (b.bestRank ?? Infinity)).slice(0, limit);
  const movement = { added: [], retained: [], exited: [] };
  if (comparison?.topItems) {
    const before = new Set(comparison.topItems.map((item) => item.shopTitle).filter(Boolean));
    const after = new Set(input.topItems.map((item) => item.shopTitle).filter(Boolean));
    movement.added = [...after].filter((shop) => !before.has(shop));
    movement.retained = [...after].filter((shop) => before.has(shop));
    movement.exited = [...before].filter((shop) => !after.has(shop));
  }
  const sampleOnly = input.completeness?.completeForRequestedTop !== true;
  return {
    categoryId: input.categoryId || input.cateId || null,
    dateRange: input.dateRange || null,
    rankType: input.rankType || null,
    completeness: input.completeness || null,
    shopCount: rows.size,
    topShops,
    concentration: { top1: topShops.slice(0, 1).reduce((sum, row) => sum + row.itemCount, 0) / (denominator || 1), top3: topShops.slice(0, 3).reduce((sum, row) => sum + row.itemCount, 0) / (denominator || 1), scope: sampleOnly ? 'retrieved-sample' : 'requested-top-n' },
    movement,
    dataGaps: sampleOnly ? ['The ranking is incomplete; shares describe only the retrieved sample.'] : []
  };
}
