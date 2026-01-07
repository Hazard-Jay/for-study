const $ = (id) => document.getElementById(id)

const state = {
  nodes: [],
  details: null,
  topo: null,
  pushGet: null,
  pushPost: null,
  timer: null,
  postTimer: null,
  lastPostTs: 0
}

const macRe = /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$/

async function fetchJson(url, opts) {
  const res = await fetch(url, opts)
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  return { ok: res.ok, status: res.status, data }
}

function nowStr() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function tsStr(tsSec) {
  if (!tsSec) return ""
  const d = new Date(Number(tsSec) * 1000)
  const p = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function setStatus(el, kind, text) {
  el.classList.remove("ok","bad","warn")
  if (kind) el.classList.add(kind)
  el.textContent = text
}

function copyText(t) {
  if (!t) return
  navigator.clipboard.writeText(t).catch(() => {})
}

function prettyJson(x) {
  try { return JSON.stringify(x, null, 2) } catch { return String(x) }
}

function renderTable(container, cols, rows) {
  const esc = (s) => (s ?? "").toString()
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  const head = cols.map(c => `<th>${esc(c.label)}</th>`).join("")
  const body = rows.map(r => {
    const tds = cols.map(c => `<td class="${c.mono ? "mono" : ""}">${esc(c.get(r))}</td>`).join("")
    return `<tr>${tds}</tr>`
  }).join("")
  container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`
}

function pick(obj, path, defv="") {
  try {
    const parts = path.split(".")
    let cur = obj
    for (const p of parts) {
      if (cur == null) return defv
      cur = cur[p]
    }
    return cur ?? defv
  } catch {
    return defv
  }
}

function renderNodes() {
  const q = $("nodeFilter").value.trim().toLowerCase()
  const list = $("nodeList")
  const nodes = (state.nodes || []).filter(x => !q || String(x).toLowerCase().includes(q))
  $("nodeCount").textContent = String(nodes.length)
  if (!nodes.length) {
    list.innerHTML = `<div class="small">暂无数据</div>`
    return
  }
  list.innerHTML = nodes.slice(0, 800).map(id => {
    const isSwitch = String(id).startsWith("of:")
    const badge = isSwitch ? `<span class="badge switch">SWITCH</span>` : `<span class="badge host">HOST</span>`
    return `
      <div class="item">
        <div class="left">
          <div class="id">${id}</div>
          <div class="tag">${isSwitch ? "交换机节点" : "主机节点"}</div>
        </div>
        ${badge}
      </div>
    `
  }).join("")
}

function renderDetails() {
  const d = state.details
  if (!d) {
    $("detailsStat").textContent = "devices: 0 | hosts: 0 | links: 0"
    $("devicesTable").innerHTML = `<div class="small">暂无数据</div>`
    $("hostsTable").innerHTML = `<div class="small">暂无数据</div>`
    $("linksTable").innerHTML = `<div class="small">暂无数据</div>`
    $("detailsPre").textContent = ""
    return
  }

  const devices = Array.isArray(d.devices) ? d.devices : []
  const hosts = Array.isArray(d.hosts) ? d.hosts : []
  const links = Array.isArray(d.links) ? d.links : []

  $("detailsStat").textContent = `devices: ${devices.length} | hosts: ${hosts.length} | links: ${links.length}`
  $("detailsPre").textContent = prettyJson(d)

  renderTable($("devicesTable"), [
    { label: "id", mono: true, get: (r) => pick(r, "id") },
    { label: "type", get: (r) => pick(r, "type") },
    { label: "available", get: (r) => String(pick(r, "available", "")) },
    { label: "role", get: (r) => pick(r, "role") }
  ], devices.slice(0, 200))

  renderTable($("hostsTable"), [
    { label: "id", mono: true, get: (r) => pick(r, "id") },
    { label: "ipAddresses", mono: true, get: (r) => (pick(r, "ipAddresses", []) || []).join(", ") },
    { label: "location", mono: true, get: (r) => {
      const loc = (pick(r, "locations", []) || [])[0]
      if (!loc) return ""
      return `${pick(loc, "elementId")} / ${pick(loc, "port")}`
    }}
  ], hosts.slice(0, 200))

  renderTable($("linksTable"), [
    { label: "src", mono: true, get: (r) => `${pick(r, "src.device")} / ${pick(r, "src.port")}` },
    { label: "dst", mono: true, get: (r) => `${pick(r, "dst.device")} / ${pick(r, "dst.port")}` },
    { label: "state", get: (r) => pick(r, "state") },
    { label: "type", get: (r) => pick(r, "type") }
  ], links.slice(0, 400))
}

function renderTopo() {
  $("topoPre").textContent = state.topo ? prettyJson(state.topo) : ""
}

function renderPushTo(prefix, env) {
  const metaEl = $(prefix === "Get" ? "pushMetaGet" : "pushMetaPost")
  const pathEl = $(prefix === "Get" ? "pathViewGet" : "pathViewPost")
  const tableEl = $(prefix === "Get" ? "flowTableGet" : "flowTablePost")
  const preEl = $(prefix === "Get" ? "pushPreGet" : "pushPrePost")

  if (!env || !env.payload) {
    metaEl.textContent = prefix === "Get" ? "尚未执行" : "暂无 POST"
    pathEl.innerHTML = ""
    tableEl.innerHTML = `<div class="small">暂无</div>`
    preEl.textContent = ""
    return
  }

  const r = env.payload
  const path = Array.isArray(r.path) ? r.path : []
  const total = r.totalCost ?? r.total_delay_ms ?? ""
  const failed = Array.isArray(r.failed) ? r.failed : []
  const flowResults = Array.isArray(r.flowResults) ? r.flowResults : []

  metaEl.textContent = `ts=${tsStr(env.ts)} | http=${env.httpStatus} | hops=${path.length} | totalCost=${total} | failed=${failed.length}`
  preEl.textContent = prettyJson(env)

  pathEl.innerHTML = path.map((n, i) => {
    const node = `<span class="node">${n}</span>`
    const arrow = i === path.length - 1 ? "" : `<span class="arrow">→</span>`
    return node + arrow
  }).join("")

  renderTable(tableEl, [
    { label: "device", mono: true, get: (x) => x.device ?? "" },
    { label: "dir", get: (x) => x.dir ?? "" },
    { label: "outPort", mono: true, get: (x) => x.outPort ?? "" },
    { label: "code", get: (x) => String(x.code ?? "") },
    { label: "resp", mono: true, get: (x) => {
      const t = x.resp ?? ""
      if (typeof t !== "string") return prettyJson(t)
      return t.length > 160 ? t.slice(0, 160) + "…" : t
    }}
  ], flowResults)
}

async function refreshAll() {
  const t0 = Date.now()
  try {
    const [n, d, topo] = await Promise.all([
      fetchJson("/node"),
      fetchJson("/details"),
      fetchJson("/topo")
    ])

    state.nodes = n.ok && Array.isArray(n.data) ? n.data : []
    state.details = d.ok ? d.data : null
    state.topo = topo.ok ? topo.data : null

    renderNodes()
    renderDetails()
    renderTopo()

    $("lastRefresh").textContent = `${nowStr()}（${Date.now()-t0}ms）`
  } catch {
    $("lastRefresh").textContent = `${nowStr()}（刷新失败）`
  }
}

async function doPushFlowsGet() {
  const srcMac = $("srcMacGet").value.trim()
  const dstMac = $("dstMacGet").value.trim()
  const deviceId = $("deviceIdGet").value.trim()

  if (!macRe.test(srcMac) || !macRe.test(dstMac)) {
    setStatus($("pushStatusGet"), "warn", "MAC 格式不正确")
    return
  }

  setStatus($("pushStatusGet"), "warn", "请求中…")

  const qs = new URLSearchParams({ srcMac, dstMac })
  if (deviceId) qs.set("deviceId", deviceId)

  try {
    const r = await fetchJson(`/pushFlows?${qs.toString()}`, { method: "GET" })
    state.pushGet = {
      ts: Date.now() / 1000,
      httpStatus: r.status,
      payload: r.data
    }
    renderPushTo("Get", state.pushGet)

    if (r.ok) setStatus($("pushStatusGet"), "ok", `成功（HTTP ${r.status}）`)
    else setStatus($("pushStatusGet"), "bad", `失败（HTTP ${r.status}）`)
  } catch {
    setStatus($("pushStatusGet"), "bad", "请求异常")
  }
}

async function pollPostResult() {
  try {
    const r = await fetchJson("/pushFlowsLastPost")
    if (!r.ok || !r.data) return
    const ts = Number(r.data.ts || 0)
    if (!ts || ts <= state.lastPostTs) return
    state.lastPostTs = ts
    state.pushPost = r.data
    renderPushTo("Post", state.pushPost)

    const code = Number(r.data.httpStatus || 0)
    if (code >= 200 && code < 300) setStatus($("pushStatusPost"), "ok", `收到新 POST（HTTP ${code}）`)
    else setStatus($("pushStatusPost"), "bad", `收到新 POST（HTTP ${code}）`)
  } catch {}
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab")
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.getAttribute("data-tab")
      document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"))
      document.querySelectorAll(".tabpane").forEach(x => x.classList.remove("active"))
      btn.classList.add("active")
      const pane = document.getElementById(key)
      if (pane) pane.classList.add("active")
    })
  })
}

function setupAutoRefresh() {
  const apply = () => {
    if (state.timer) clearInterval(state.timer)
    const enabled = $("autoRefresh").checked
    const itv = parseInt($("refreshItv").value, 10)
    if (enabled) state.timer = setInterval(refreshAll, itv)
  }
  $("autoRefresh").addEventListener("change", apply)
  $("refreshItv").addEventListener("change", apply)
  apply()
}

function setupPostPolling() {
  if (state.postTimer) clearInterval(state.postTimer)
  state.postTimer = setInterval(pollPostResult, 1000)
}

function bindActions() {
  $("btnRefresh").addEventListener("click", refreshAll)
  $("nodeFilter").addEventListener("input", renderNodes)

  $("btnCopyDetails").addEventListener("click", () => copyText(prettyJson(state.details)))
  $("btnCopyTopo").addEventListener("click", () => copyText(prettyJson(state.topo)))

  $("btnPushGet").addEventListener("click", doPushFlowsGet)
  $("btnClearGet").addEventListener("click", () => {
    state.pushGet = null
    renderPushTo("Get", null)
    setStatus($("pushStatusGet"), "", "空闲")
  })
  $("btnCopyGet").addEventListener("click", () => copyText(prettyJson(state.pushGet)))

  $("btnClearPost").addEventListener("click", () => {
    state.pushPost = null
    renderPushTo("Post", null)
    setStatus($("pushStatusPost"), "", "监听中")
  })
  $("btnCopyPost").addEventListener("click", () => copyText(prettyJson(state.pushPost)))

  $("srcMacGet").addEventListener("keydown", (e) => { if (e.key === "Enter") doPushFlowsGet() })
  $("dstMacGet").addEventListener("keydown", (e) => { if (e.key === "Enter") doPushFlowsGet() })
  $("deviceIdGet").addEventListener("keydown", (e) => { if (e.key === "Enter") doPushFlowsGet() })
}

async function boot() {
  setupTabs()
  bindActions()
  setupAutoRefresh()
  setupPostPolling()
  await refreshAll()
  await pollPostResult()
  renderPushTo("Get", null)
  renderPushTo("Post", null)
}

boot()
