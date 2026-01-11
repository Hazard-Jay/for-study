import heapq
import random
import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response
from .config import settings
from collections import defaultdict
from. import topo

def delay_weight(u, v, info):
    """
    根据设备 u 和 v 之间的连接信息返回时延
    :param u: 源设备 ID
    :param v: 目标设备 ID
    :param info: 设备 u 和 v 之间的连接信息（字典）
    :return: 从 u 到 v 的时延（单位：毫秒）
    """
    # 获取连接信息
    for neighbor, ports in info[u]:
        if neighbor == v:
            # 获取连接的端口
            src_port = ports["srcPort"]
            dst_port = ports["dstPort"]

            # 从数据库获取时延（设备 v 和目标端口 dst_port）
            delay = get_delay_from_db(v, dst_port)
            if delay is not None:
                return delay  # 返回数据库中的时延
            else:
                # 如果数据库没有时延信息，可以返回一个默认的时延值
                return random.randint(1, 100)  # 随机生成一个时延，单位为毫秒
    
    # 如果找不到设备 u 到设备 v 的连接信息，返回一个默认的时延
    return 1  # 默认时延为 1 毫秒

def dijkstra(adj, src, dst, weight=delay_weight):
    """
    adj: dict[node] = list of (neighbor, link_info)
    src, dst: 起点节点ID、终点节点ID（可以是交换机ID或host ID）
    weight: 函数 weight(u, v, link_info) -> float（时延）
    """

    # dist[v]：从src到v的当前最小时延
    dist = {}
    prev = {}

    # 初始化起点
    dist[src] = 0.0
    prev[src] = None

    # 小根堆 (当前距离, 节点)
    pq = [(0.0, src)]

    visited = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        # 提前终止：已经取出目标节点
        if u == dst:
            break

        for v in adj.get(u, []):
            w = weight(u, v, adj)
            nd = d + w

            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    # 无法到达
    if dst not in dist:
        return None, float('inf')

    # 反向回溯重建路径
    path = []
    cur = dst
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()

    return path, dist[dst]
