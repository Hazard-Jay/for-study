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

def save_all(details_obj, topo_obj, node_obj, keep=10):
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
