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
import threading
import time
from db.topoSave import save_all,load_topo, load_details, load_node,save_device_delay_data

LAST_GET = {"ts": 0.0, "httpStatus": 0, "payload": None}
LAST_POST = {"ts": 0.0, "httpStatus": 0, "payload": None}

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

@app.get("/node")
async def node(request):
    return response.json(load_node())

@app.get("/details")
async def details(request):
    return response.json(load_details())
@app.get("/topo")
async def topo(request):
    return response.json(load_topo())

@app.get("/path")
async def path(request):
    src = request.args.get("src")  # e.g. "00:00:00:00:00:01/None"
    dst = request.args.get("dst")  # e.g. "00:00:00:00:00:02/None"

    if not src or not dst:
        return response.json(
            {"error": "src and dst query params are required"},
            status=400
        )

    data = load_topo()
    if data is None:
        data = service.topo.getTopo(settings.onos.url)
    path, total_delay = dijkstra(data, src, dst)

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
    payload, status = pushflows(data.get("srcMac"), data.get("dstMac"), data.get("deviceId"))
    LAST_POST["ts"] = time.time()
    LAST_POST["httpStatus"] = int(status)
    LAST_POST["payload"] = payload
    return response.json(payload, status=status)

@app.get("/pushFlows")
async def pushflows_get(request):
    payload, status = pushflows(request.args.get("srcMac"), request.args.get("dstMac"), request.args.get("deviceId"))
    LAST_GET["ts"] = time.time()
    LAST_GET["httpStatus"] = int(status)
    LAST_GET["payload"] = payload
    return response.json(payload, status=status)

@app.post("/delays")
async def delays_post(request: Request):
    data = request.json()  # 获取 JSON 数据
    device_id = data.get("deviceId")
    port = data.get("port")
    delay = data.get("delay")
    if not device_id or not port or delay is None:
        raise HTTPException(status_code=400, detail="Missing deviceId, port, or delay in request")

    # 调用数据库存储函数
    try:
        sid = save_device_delay_data(device_id, port, delay)
        return JSONResponse(content={"status": "success", "sid": sid}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
@app.get("/pushFlowsLastGet")
async def pushflows_last_get(request):
    return response.json(LAST_GET)

@app.get("/pushFlowsLastPost")
async def pushflows_last_post(request):
    return response.json(LAST_POST)

def poll_save_loop():
    while True:
        try:
            details = service.topo.getDetails(settings.onos.url)
            topo = service.topo.getTopo(settings.onos.url)
            node = service.topo.getNode(settings.onos.url)
            save_all(details, topo, node)
            # print("saved cache", time.time())
        except Exception as e:
            print("poll_save_loop error:", repr(e))
        time.sleep(settings.poll.topoItl)

if __name__ == "__main__":
    threading.Thread(target=poll_save_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, single_process=True)