import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response
import os
import service.topo
from service.config import settings
import heapq
import random
from service.route import dijkstra
from collections import defaultdict
from service.pushflows import pushflows

app=Sanic("SDN")
app.config.FALLBACK_ERROR_FORMAT = "json"

# 静态目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# 注册静态路由：/static/* -> web/static/*
app.static('/static', STATIC_DIR)

@app.get('/')
async def index(request):
    return await response.file(os.path.join(STATIC_DIR, 'index.html'))


# 把未被你显式处理的异常的“兜底（fallback）错误响应格式”设为 JSON。
# 等价解释：当请求触发了未捕获异常，而你又没有自定义错误处理器时，Sanic 会按 FALLBACK_ERROR_FORMAT 生成响应；设为 "json" 就会返回 {"status":500, "message": "...", ...} 之类的 JSON。

onosHost='127.0.0.1'
auth= HTTPBasicAuth("karaf", "karaf")

@app.get("/node")
async def node(request):
    return response.json(service.topo.getNode())

@app.get("/details")
async def details(request):
    return response.json(service.topo.getDetails())

@app.get("/topo")
async def topo(request):
    return response.json(service.topo.getTopo())

@app.get("/path")
async def path(request):
    src = request.args.get("src")  # e.g. "00:00:00:00:00:01/None"
    dst = request.args.get("dst")  # e.g. "00:00:00:00:00:02/None"

    if not src or not dst:
        return response.json(
            {"error": "src and dst query params are required"},
            status=400
        )

    adj = service.topo.getTopo()
    path, total_delay = dijkstra(adj, src, dst)

    if path is None:
        return response.json(
            {"error": f"No path from {src} to {dst}"},
            status=404
        )

    return response.json(
        {
            "src": src,
            "dst": dst,
            "path": path,
            "total_delay_ms": total_delay
        }
    )

@app.post("/pushFlows")
async def pushflows_post(request):
    data = request.json or {}
    payload, status = pushflows(data.get("srcMac"), data.get("dstMac"))
    return response.json(payload, status=status)

@app.get("/pushFlows")
async def pushflows_get(request):
    payload, status = pushflows(request.args.get("srcMac"), request.args.get("dstMac"))
    return response.json(payload, status=status)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, single_process=True)