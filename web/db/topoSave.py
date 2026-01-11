import json
import pymysql
from service.config import settings

def connect():
    return pymysql.connect(
        host=settings.db.host,
        port=settings.db.port,
        user=settings.db.user,
        password=settings.db.password,
        database=settings.db.database,
        charset=settings.db.charset,
        autocommit=True
    )

def _loads(x):
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    if isinstance(x, (bytes, bytearray)):
        x = x.decode("utf-8")
    return json.loads(x)

def save_all(details_obj, topo_obj, node_obj, keep=100):
    details_s = json.dumps(details_obj, ensure_ascii=False)
    topo_s = json.dumps(topo_obj, ensure_ascii=False)
    node_s = json.dumps(node_obj, ensure_ascii=False)

    conn = connect()
    conn.autocommit(False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO onos_details_cache(details_json) VALUES (CAST(%s AS JSON))",
                (details_s,)
            )
            sid = cur.lastrowid

            cur.execute(
                "INSERT INTO onos_topo_cache(id, topo_json) VALUES (%s, CAST(%s AS JSON))",
                (sid, topo_s)
            )
            cur.execute(
                "INSERT INTO onos_node_cache(id, node_json) VALUES (%s, CAST(%s AS JSON))",
                (sid, node_s)
            )

            cur.execute(
                "DELETE FROM onos_details_cache WHERE id NOT IN "
                "(SELECT id FROM (SELECT id FROM onos_details_cache ORDER BY id DESC LIMIT %s) t)",
                (int(keep),)
            )
            cur.execute(
                "DELETE FROM onos_topo_cache WHERE id NOT IN "
                "(SELECT id FROM (SELECT id FROM onos_details_cache ORDER BY id DESC LIMIT %s) t)",
                (int(keep),)
            )
            cur.execute(
                "DELETE FROM onos_node_cache WHERE id NOT IN "
                "(SELECT id FROM (SELECT id FROM onos_details_cache ORDER BY id DESC LIMIT %s) t)",
                (int(keep),)
            )

        conn.commit()
        return sid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def save_device_delay_data(device_id, port, delay, keep=100):
    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # 插入设备信息、端口和时延数据
            cur.execute(
                "INSERT INTO device_delay_data(device_id, port, delay) "
                "VALUES (%s, %s, %s) RETURNING id",
                (device_id, port, delay)
            )
            sid = cur.fetchone()[0]  # 获取插入的记录的 ID

            # 删除超过数量限制的历史数据
            cur.execute(
                "DELETE FROM device_delay_data WHERE id NOT IN "
                "(SELECT id FROM (SELECT id FROM device_delay_data ORDER BY id DESC LIMIT %s) t)",
                (int(keep),)
            )

        conn.commit()
        return sid  # 返回插入数据的 ID
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def load_details():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT details_json FROM onos_details_cache ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            return _loads(row[0])
    finally:
        conn.close()

def load_topo():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT topo_json FROM onos_topo_cache ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            return _loads(row[0])
    finally:
        conn.close()

def load_node():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT node_json FROM onos_node_cache ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            return _loads(row[0])
    finally:
        conn.close()

def get_delay_from_db(device_id_v, dst_port):
    """根据目的设备 ID 和目的端口号查询设备之间的时延"""
    conn = connect()
    try:
        with conn.cursor() as cur:
            # 查询设备 v 和端口 dst_port 对应的设备 u 和端口 src_port 的时延
            cur.execute("""
                SELECT device_id, port, delay 
                FROM device_delay_data
                WHERE device_id = %s AND port = %s
            """, (device_id_v, dst_port))
            
            row = cur.fetchone()
            if row:
                # 如果找到，返回设备 u 和端口的时延
                device_id_u, port, delay = row
                return delay  # 返回时延
            else:
                return None  # 如果没有找到时延，返回 None
    finally:
        conn.close()


def fetch_topology_data():
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM devices")
            devices = cur.fetchall()
            cur.execute("SELECT id, ipAddress FROM hosts")
            hosts = cur.fetchall()
            cur.execute("SELECT src_device, dst_device, src_port, dst_port FROM links")
            links = cur.fetchall()

        return {"devices": devices, "hosts": hosts, "links": links}
    finally:
        conn.close()
