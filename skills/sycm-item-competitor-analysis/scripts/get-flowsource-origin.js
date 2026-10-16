/**
 * 获取流量来源平铺列表（支持 indexCode: uv/payRate/payByrCnt），同时返回本品和竞品数据
 * @api api-164
 * @method GET
 * @endpoint /mc/rivaItem/analysis/getFlowSource/origin/v4/free.json
 */
// 超时与有限重试封装（timeout + retry + 指数退避 backoff）。
// 只对幂等 GET 生效；兜底 fallback：重试仍失败时向上抛错，由上层 SKILL.md 兜底/降级路径处理（停止并询问用户，不做数据编造）。
async function fetchWithTimeoutRetry(url, opts, cfg) {
  const timeout = (cfg && cfg.timeout) || 30000;
  const retries = (cfg && cfg.retries) || 2;
  const backoff = (cfg && cfg.backoff) || 500;
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController();
    const timer = setTimeout(function () { ctrl.abort(); }, timeout);
    try {
      const r = await fetch(url, Object.assign({}, opts, { signal: ctrl.signal }));
      clearTimeout(timer);
      // 429/5xx 触发有限退避重试；成功或 4xx（除 429）直接返回，交由业务层判断
      if ((r.status === 429 || r.status >= 500) && attempt < retries) {
        lastErr = new Error("HTTP " + r.status + " retry");
        await new Promise(function (res) { setTimeout(res, backoff * Math.pow(3, attempt)); });
        continue;
      }
      return r;
    } catch (e) {
      clearTimeout(timer);
      lastErr = e;
      // 超时或网络错误：有限重试；仍失败则由调用方走兜底/降级停止路径
      if (attempt < retries) {
        await new Promise(function (res) { setTimeout(res, backoff * Math.pow(3, attempt)); });
        continue;
      }
      throw e;
    }
  }
  throw lastErr;
}

module.exports = async function get_flowsource_origin(params = {}) {
  const qp = new URLSearchParams();
  qp.set("dateRange", params.dateRange || "2026-08-05|2026-08-11");
  qp.set("dateType", params.dateType || "recent7");
  qp.set("indexCode", params.indexCode || "uv");
  qp.set("order", params.order || "desc");
  const idxCode = params.indexCode || "uv";
  qp.set("orderBy", params.orderBy || idxCode);
  qp.set("page", params.page || 1);
  qp.set("pageSize", params.pageSize || 30);
  qp.set("rivalItem1Id", params.rivalItem1Id || "861895294478");
  qp.set("selfItemId", params.selfItemId || "692941946548");
  qp.set("flowBizType", "classic");
  qp.set("marketVersion", "free");
  qp.set("pageType", "item");
  const url = `https://sycm.taobao.com/mc/rivaItem/analysis/getFlowSource/origin/v4/free.json?` + qp.toString();
  const resp = await fetchWithTimeoutRetry(url, { method: "GET", credentials: "include" }, { timeout: 30000, retries: 2, backoff: 500 });
  let json;
  try {
    json = await resp.json();
  } catch (e) {
    // JSON 解析失败：走兜底策略，返回 ok=false 交由上层停止并询问用户，不做重试或数据编造
    return { ok: false, code: "PARSE_ERROR", message: String((e && e.message) || e), traceId: null };
  }
  if (json.code !== 0) {
    return { ok: false, code: json.code, message: json.message || "API error", traceId: json.traceId };
  }
  return { ok: true, data: json.data, traceId: json.traceId };
};
