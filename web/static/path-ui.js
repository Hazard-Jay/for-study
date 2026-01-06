const $ = (id) => document.getElementById(id)

const state = {
  topoRaw: null,
  nodes: null,
  edges: null,
  network: null,
  selectedSrc: null,
  selectedDst: null,
  pathEdges: new Set(),
  pathNodes: new Set()
}

const setStatus = (s) => { $("status").textContent = s }
const pretty = (obj) => JSON.stringify(obj, null, 2)

window.addEventListener("error", (e) => {
  const out = $("out")
  if (out) out.textContent = String(e.message || e.error || e)
})

const fetchJson = async (path) => {
  const res = await fetch(path)
  const text = await res.text()
  let data = null
  try { data = JSON.parse(text) } catch { data = { raw: text } }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}\n${pretty(data)}`)
  return data
}

const hostIdToMac = (hostId) => {
  if (!hostId) return ""
  const s = String(hostId)
  const i = s.indexOf("/")
  return (i >= 0 ? s.slice(0, i) : s).toLowerCase()
}

const buildGraph = (details) => {
  const devices = details.devices || []
  const hosts = details.hosts || []
  const links = details.links || []

  const nodes = []
  const edges = []
  const seen = new Set()

  for (const d of devices) {
    const id = d.id
    if (!id || seen.has(id)) continue
    seen.add(id)
    const label = id.startsWith("of:") ? `SW\n${id.slice(-4)}` : id
    nodes.push({ id, label, group: "switch" })
  }

  for (const h of hosts) {
    const id = h.id
    if (!id || seen.has(id)) continue
    seen.add(id)
    const ip = (h.ipAddresses && h.ipAddresses[0]) ? h.ipAddresses[0] : ""
    const mac = hostIdToMac(id)
    const label = ip ? `H\n${ip}` : `H\n${mac.slice(-4)}`
    nodes.push({ id, label, group: "host" })
  }

  for (const l of links) {
    const u = l.src && l.src.device
    const v = l.dst && l.dst.device
    if (!u || !v) continue
    const sp = l.src.port
    const dp = l.dst.port
    const eid = `${u}:${sp}->${v}:${dp}`
    edges.push({ id: eid, from: u, to: v, label: `${sp}→${dp}` })
  }

  for (const h of hosts) {
    const hid = h.id
    const locs = h.locations || []
    for (const loc of locs) {
      const sid = loc.elementId
      const p = loc.port
      if (!sid || !hid) continue
      const eid = `${sid}:${p}->${hid}`
      edges.push({ id: eid, from: sid, to: hid, label: `${p}` })
    }
  }

  return { nodes, edges }
}

const renderNetwork = (nodesArr, edgesArr) => {
  if (!window.vis) {
    $("out").textContent = "vis-network 未加载，请确认 /static/vis-network.min.js 可访问"
    return
  }

  const container = $("network")
  state.nodes = new vis.DataSet(nodesArr)
  state.edges = new vis.DataSet(edgesArr)

  const options = {
    physics: { enabled: true, stabilization: { iterations: 150 } },
    interaction: { hover: true, multiselect: false },
    nodes: { shape: "dot", font: { size: 14 } },
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.6 } }, font: { size: 12 }, smooth: true },
    groups: {
      switch: { shape: "box" },
      host: { shape: "ellipse" }
    }
  }

  state.network = new vis.Network(container, { nodes: state.nodes, edges: state.edges }, options)

  state.network.on("click", (params) => {
    const ns = params.nodes || []
    if (ns.length !== 1) return
    const id = ns[0]
    const isHost = String(id).includes("/")
    if (!isHost) {
      $("out").textContent = `已点击节点：${id}`
      return
    }

    if (!state.selectedSrc || (state.selectedSrc && state.selectedDst)) {
      state.selectedSrc = id
      state.selectedDst = null
    } else {
      state.selectedDst = id
    }

    $("srcHostId").value = state.selectedSrc || ""
    $("dstHostId").value = state.selectedDst || ""
    if (state.selectedSrc) $("srcMac").value = hostIdToMac(state.selectedSrc)
    if (state.selectedDst) $("dstMac").value = hostIdToMac(state.selectedDst)

    $("out").textContent = `SRC=${state.selectedSrc || ""}\nDST=${state.selectedDst || ""}`
  })
}

const clearHighlights = () => {
  if (!state.edges) return
  for (const id of state.pathEdges) {
    const e = state.edges.get(id)
    if (e) state.edges.update({ id, width: undefined, dashes: undefined })
  }
  for (const id of state.pathNodes) {
    const n = state.nodes.get(id)
    if (n) state.nodes.update({ id, borderWidth: undefined })
  }
  state.pathEdges.clear()
  state.pathNodes.clear()
}

const highlightPath = (path) => {
  clearHighlights()
  if (!Array.isArray(path) || path.length < 2) return

  for (const n of path) {
    if (state.nodes.get(n)) {
      state.nodes.update({ id: n, borderWidth: 4 })
      state.pathNodes.add(n)
    }
  }

  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i]
    const b = path[i + 1]
    const candidates = state.edges.get({
      filter: (e) => (e.from === a && e.to === b) || (e.from === b && e.to === a)
    })
    for (const e of candidates) {
      state.edges.update({ id: e.id, width: 4, dashes: false })
      state.pathEdges.add(e.id)
    }
  }
}

const refresh = async () => {
  setStatus("加载中...")
  try {
    const details = await fetchJson("/details")
    state.topoRaw = details
    $("out").textContent = pretty(details)
    const g = buildGraph(details)
    renderNetwork(g.nodes, g.edges)
    setStatus(`已加载：devices=${(details.devices || []).length} hosts=${(details.hosts || []).length} links=${(details.links || []).length}`)
  } catch (e) {
    setStatus("加载失败")
    $("out").textContent = String(e)
  }
}

const getPath = async () => {
  const src = $("srcHostId").value.trim()
  const dst = $("dstHostId").value.trim()
  if (!src || !dst) {
    $("pathBox").textContent = "请先选择 src/dst（点击拓扑里的 host）"
    return
  }
  setStatus("计算路径中...")
  try {
    const data = await fetchJson(`/path?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`)
    $("out").textContent = pretty(data)
    const p = data.path || []
    $("pathBox").textContent = p.length ? p.join(" -> ") : "无路径"
    highlightPath(p)
    setStatus("路径已返回")
  } catch (e) {
    $("pathBox").textContent = String(e)
    setStatus("路径计算失败")
  }
}

const pushFlows = async () => {
  const srcMac = $("srcMac").value.trim()
  const dstMac = $("dstMac").value.trim()
  if (!srcMac || !dstMac) {
    $("out").textContent = "请填写 srcMac / dstMac"
    return
  }
  setStatus("下发流表中...")
  try {
    const data = await fetchJson(`/pushFlows?srcMac=${encodeURIComponent(srcMac)}&dstMac=${encodeURIComponent(dstMac)}`)
    $("out").textContent = pretty(data)
    const p = data.path || []
    $("pathBox").textContent = p.length ? p.join(" -> ") : "无路径"
    highlightPath(p)
    setStatus("下发完成")
  } catch (e) {
    $("out").textContent = String(e)
    setStatus("下发失败")
  }
}

const clearSelect = () => {
  state.selectedSrc = null
  state.selectedDst = null
  $("srcHostId").value = ""
  $("dstHostId").value = ""
  $("srcMac").value = ""
  $("dstMac").value = ""
  $("pathBox").textContent = ""
  clearHighlights()
  setStatus("已清空")
}

const bind = () => {
  $("btnRefresh").onclick = refresh
  $("btnClear").onclick = clearSelect
  $("btnPath").onclick = getPath
  $("btnPush").onclick = pushFlows

  $("btnDetails").onclick = async () => {
    try { $("out").textContent = pretty(await fetchJson("/details")) } catch (e) { $("out").textContent = String(e) }
  }
  $("btnTopo").onclick = async () => {
    try { $("out").textContent = pretty(await fetchJson("/topo")) } catch (e) { $("out").textContent = String(e) }
  }
  $("btnNodes").onclick = async () => {
    try { $("out").textContent = pretty(await fetchJson("/node")) } catch (e) { $("out").textContent = String(e) }
  }
}

bind()
refresh()
