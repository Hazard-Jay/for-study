import service.topo
from service.route import dijkstra

def _install_bidirectional_flows(adj, path, src_mac, dst_mac):
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
                service.topo.push_flow(node, src_mac, dst_mac, out_fwd)

        if i - 1 >= 0:
            prv = path[i - 1]
            out_rev = None
            for nb, info in adj.get(node, []):
                if nb == prv:
                    out_rev = info.get("srcPort")
                    break
            if out_rev is not None:
                service.topo.push_flow(node, dst_mac, src_mac, out_rev)

def pushflows(src_mac, dst_mac):
    if not src_mac or not dst_mac:
        return {"error": "srcMac and dstMac are required"}, 400

    topo_raw = service.topo.getDetails()
    adj = service.topo.getTopo()

    src_host_id = service.topo.findId(topo_raw, src_mac)
    dst_host_id = service.topo.findId(topo_raw, dst_mac)

    if not src_host_id or not dst_host_id:
        return {
            "error": "host not found",
            "srcHostId": src_host_id,
            "dstHostId": dst_host_id
        }, 404

    path, total_cost = dijkstra(adj, src_host_id, dst_host_id)
    if not path:
        return {"error": "no path between hosts"}, 404

    _install_bidirectional_flows(adj, path, src_mac, dst_mac)

    device_ids = [n for n in path if n.startswith("of:")]
    return {
        "srcMac": src_mac,
        "dstMac": dst_mac,
        "srcHostId": src_host_id,
        "dstHostId": dst_host_id,
        "path": path,
        "deviceIds": device_ids,
        "totalCost": total_cost
    }, 200
