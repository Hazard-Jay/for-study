import heapq
import random
import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response
from .config import settings
from collections import defaultdict
from service.route import dijkstra

def getDevices(l):
    url = f"{l}/devices"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth,timeout=2)
    return res.json()

def getLinks(l):
    url = f"{l}/links"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth,timeout=2)
    return res.json()

def getHosts(l):
    url = f"{l}/hosts"
    res=requests.get(url=url, headers=settings.onos.headers, auth=settings.onos.auth,timeout=2)
    return res.json()

def getDetails(l):
    devices=getDevices(l)
    hosts=getHosts(l)
    links=getLinks(l)
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

def getNode(l):
    topo=getDetails(l)
    adj = []

    for node in topo["devices"]:
        adj.append(node["id"])

    for node in topo["hosts"]:
        adj.append(node["id"])
    
    return adj

def getTopo(l):
    # 获取邻接表

    topo=getDetails(l)
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
              priority=40001, permanent=True, timeout=0):
    url = f"{settings.onos.url}/flows/{device_id}"

    # 定义不同的 ethType 列表
    eth_types = ["0x0800", "0x806", "0x88cc", "0x8942"]  # IPv4, ARP, LLDP, MPLS
    
    for ethType in eth_types:
        # 为每个 ethType 下发流表
        flow = {
            "priority": int(priority),
            "isPermanent": bool(permanent),
            "timeout": int(timeout),
            "deviceId": device_id,
            "treatment": {
                "instructions": [
                    {"type": "OUTPUT", "port": str(out_port)}  # 输出到指定端口
                ]
            },
            "selector": {
                "criteria": [
                    {"type": "ETH_TYPE", "ethType": ethType},  # 根据 ethType 匹配
                    {"type": "ETH_SRC", "mac": src_mac},  # 匹配源 MAC 地址
                    {"type": "ETH_DST", "mac": dst_mac}   # 匹配目标 MAC 地址
                ]
            }
        }

        # 发送 POST 请求下发流表
        res = requests.post(
            url=url,
            json=flow,
            headers=settings.onos.headers,
            auth=settings.onos.auth,
            timeout=2
        )

    return res.status_code, res.text

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
