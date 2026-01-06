import heapq
import random
import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response
from .config import settings
from collections import defaultdict
from service.route import dijkstra


def getDevices():
    url = f"{settings.onos.url}/devices"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth)
    return res.json()

def getLinks():
    url = f"{settings.onos.url}/links"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth)
    return res.json()

def getHosts():
    url = f"{settings.onos.url}/hosts"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth)
    return res.json()

def getDetails():
    devices=getDevices()
    hosts=getHosts()
    links=getLinks()
    topo_raw = {
        "devices": devices.get("devices", []),
        "links":   links.get("links", []),
        "hosts":   hosts.get("hosts", [])
    }
    return topo_raw

#     topo_raw = {
#     "devices": [
#         {"id": "of:0000000000000001", "type": "SWITCH", ...},
#         {"id": "of:0000000000000002", "type": "SWITCH", ...},
#         {"id": "of:0000000000000003", "type": "SWITCH", ...},
#     ],
#     "links": [
#         {"src": {"device": "of:0000000000000001", "port": "1"},
#          "dst": {"device": "of:0000000000000002", "port": "1"},
#          "state": "ACTIVE"},
#         {"src": {"device": "of:0000000000000002", "port": "2"},
#          "dst": {"device": "of:0000000000000003", "port": "1"},
#          "state": "ACTIVE"},
#     ],
#     "hosts": [
#         {"id": "00:00:00:00:00:01/None",
#          "ipAddresses": ["10.0.0.1"],
#          "locations": [{"elementId": "of:0000000000000001", "port": "2"}]},
#         {"id": "00:00:00:00:00:02/None",
#          "ipAddresses": ["10.0.0.2"],
#          "locations": [{"elementId": "of:0000000000000003", "port": "2"}]},
#     ]
# }

def getNode():
    topo=getDetails()
    adj = []

    for node in topo["devices"]:
        adj.append(node["id"])

    for node in topo["hosts"]:
        adj.append(node["id"])
    
    return adj

def getTopo():
    # 获取邻接表

    topo=getDetails()
    adj = defaultdict(list)

    for link in topo["links"]:
        u = link["src"]["device"]
        v = link["dst"]["device"]

        link_info_uv = {
            "srcPort": link["src"]["port"],
            "dstPort": link["dst"]["port"],
        }
        link_info_vu = {
            "srcPort": link["dst"]["port"],
            "dstPort": link["src"]["port"],
        }

        adj[u].append((v, link_info_uv))
        adj[v].append((u, link_info_vu))

    for link in topo["hosts"]:
        for u in link["locations"]:
            id=u["elementId"]
            hostId=link["id"]

        link_info_uv = {"srcPort": u["port"], "dstPort": "host"}
        link_info_vu = {"srcPort": "host", "dstPort": u["port"]}
        adj[id].append((hostId, link_info_uv))
        adj[hostId].append((id, link_info_vu))

    return adj
    # "of:0000000000000001": [
    # ("of:0000000000000002", {"srcPort": "1", "dstPort": "1"}),
    # ("00:00:00:00:00:01/None", {"srcPort": "2", "dstPort": "host"})

def push_flow(device_id, src_mac, dst_mac, out_port,
              priority=10, permanent=True, timeout=0):
    """
    在指定 device 上下发一条流表：
    match: src_mac, dst_mac, IPv4
    action: OUTPUT out_port
    """
    url = f"{settings.onos.url}/flows/{device_id}"

    flow = {
        "priority": priority,
        "isPermanent": permanent,
        "timeout": timeout,
        "deviceId": device_id,
        "treatment": {
            "instructions": [
                {
                    "type": "OUTPUT",
                    "port": str(out_port)  # 注意字符串
                }
            ]
        },
        "selector": {
            "criteria": [
                {
                    "type": "ETH_TYPE",
                    "ethType": "0x0800"  # IPv4
                },
                {
                    "type": "ETH_SRC",
                    "mac": src_mac
                },
                {
                    "type": "ETH_DST",
                    "mac": dst_mac
                }
            ]
        }
    }

    body = {"flows": [flow]}

    res = requests.post(
        url=url,
        json=body,
        headers=settings.onos.headers,
        auth=settings.onos.auth
    )

    if res.status_code in (200, 201, 202):
        print(f"[OK] push_flow to {device_id}, {src_mac}->{dst_mac} out {out_port}")
    else:
        print(f"[ERR] push_flow status={res.status_code}, body={res.text}")

    return res

def delete_all_flows(device_id):
    """
    删除某个设备上的所有流表
    """
    url = f"{settings.onos.url}/flows/application/{device_id}"
    res = requests.delete(
        url=url,
        headers=settings.onos.headers,
        auth=settings.onos.auth
    )

    if res.status_code in (200, 202, 204):
        print(f"[OK] delete_all_flows on {device_id}")
    else:
        print(f"[ERR] delete_all_flows status={res.status_code}, body={res.text}")

    return res

def findId(topo_raw, mac):
    """
    在 topo_raw["hosts"] 里找满足 id 以 mac 开头的 host
    """
    mac = mac.lower()
    for h in topo_raw["hosts"]:
        host_id = h["id"].lower()
        if host_id.startswith(mac):
            return h["id"]
    return None
