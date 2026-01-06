import heapq
import random
import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response
from .config import settings
from collections import defaultdict
from. import topo

def delay_weight(u, v, info):
    return 1
    # return random.randint(1, 100)

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

        for v, info in adj.get(u, []):
            w = weight(u, v, info)
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
