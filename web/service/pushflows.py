import service.topo
from service.route import dijkstra
from db.topoSave import load_details, load_topo

def _find_out_port(adj, path, device_id, forward=True):
    if not device_id:
        return None
    if device_id not in path:
        return None
    idx = path.index(device_id)
    j = idx + 1 if forward else idx - 1
    if j < 0 or j >= len(path):
        return None
    nxt = path[j]
    for nb, info in adj.get(device_id, []):
        if nb == nxt:
            return info.get("srcPort")
    return None

def _install_bidirectional_flows(adj, path, src_mac, dst_mac):
    results = []
    for i, node in enumerate(path):
        if not node.startswith("of:"):
            continue
        if i + 1 < len(path):
            nxt = path[i + 1]
            out_fwd = None
            for nb, info in adj.get(node, []):
                if nb == nxt:
                    out_fwd = info.get("srcPort")
                    break
            if out_fwd is not None:
                code, text = service.topo.push_flow(node, src_mac, dst_mac, out_fwd)
                results.append({"device": node, "dir": "fwd", "outPort": out_fwd, "code": code, "resp": text})
        if i - 1 >= 0:
            prv = path[i - 1]
            out_rev = None
            for nb, info in adj.get(node, []):
                if nb == prv:
                    out_rev = info.get("srcPort")
                    break
            if out_rev is not None:
                code, text = service.topo.push_flow(node, dst_mac, src_mac, out_rev)
                results.append({"device": node, "dir": "rev", "outPort": out_rev, "code": code, "resp": text})
    return results

def pushflows(src_mac, dst_mac, device_id=None):
    if not src_mac or not dst_mac:
        return {"error": "srcMac and dstMac are required"}, 400

    topo_raw = load_details()
    adj = load_topo()

    if topo_raw is None or adj is None:
        topo_raw = service.topo.getDetails(settings.onos.url)
        adj = service.topo.getTopo(settings.onos.url)

    src_host_id = service.topo.findId(topo_raw, src_mac)
    dst_host_id = service.topo.findId(topo_raw, dst_mac)

    if not src_host_id or not dst_host_id:
        return {"error": "host not found", "srcHostId": src_host_id, "dstHostId": dst_host_id}, 404
    
    path, total_cost = dijkstra(adj, src_host_id, dst_host_id)

    if not path:
        return {"error": "no path between hosts"}, 404

    results = _install_bidirectional_flows(adj, path, src_mac, dst_mac)

    out_port = _find_out_port(adj, path, device_id, forward=True)

    bad = [r for r in results if r["code"] not in (200, 201, 202)]
    status = 502 if bad else 200

    return {
        "srcMac": src_mac,
        "dstMac": dst_mac,
        "srcHostId": src_host_id,
        "dstHostId": dst_host_id,
        "path": path,
        "totalCost": total_cost,
        "outPort": "" if out_port is None else str(out_port),
        "flowResults": results,
        "failed": bad
    }, status
