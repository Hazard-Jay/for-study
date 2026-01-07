import requests
from requests.auth import HTTPBasicAuth
from sanic import Sanic,response

# ONOS 地址、认证、定时任务配置，常量配置

class ONOSConfig:
    """
    ONOS 相关配置：
    - REST API 地址
    - 认证账号
    """
    url = "http://127.0.0.1:8181/onos/v1"
    onosHost='127.0.0.1'
    name = 'karaf'
    pwd= 'karaf'
    auth= HTTPBasicAuth("karaf", "karaf")
    headers= {"Accept": "application/json"}

class DBConfig:
    """
    数据库配置：
    """
    # # 例：sqlite:///绝对路径/data.db
    # DEFAULT_DB_PATH = BASE_DIR / "data.db"
    # URL: str = getenv("DB_URL", f"sqlite:///{DEFAULT_DB_PATH}")

    host = "192.168.241.1"
    port = 3306
    user = "sdn"
    password = "SdnPass_123!"
    database = "sdn"
    charset = "utf8mb4"

class PollingConfig:
    """
    轮询周期：
    - 多久从 ONOS 拉一次拓扑 / 节点信息
    单位都是秒
    """
    topoItl= 100

class Settings:

    onos = ONOSConfig
    db = DBConfig
    poll = PollingConfig

settings=Settings()