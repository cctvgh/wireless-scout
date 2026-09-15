#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无线环境勘察系统 (WireScout) - 本地勘察服务
============================================
基于 Python 标准库实现的本地无线环境勘察与可视化服务。

功能（全部为被动/只读勘察，遵守合规红线）：
  1. WiFi 勘察     : 调用系统无线网卡可见网络列表（netsh），解析 SSID/BSSID/信号/信道/加密
  2. 遥测数据导入   : CSV / GeoJSON / KML 站点数据入库（自动列映射）
  3. 基站信息查询   : 通过公开数据库 OpenCellID（可选 API Key）查询区域基站
  4. 勘察报告生成   : 汇总统计（AP 数量、加密分布、信道占用、信号质量）
  5. 数据导出       : CSV / GeoJSON / HTML 报告

安全红线（禁止）：
  - 不做任何主动攻击、破解、注入、拒绝服务
  - 不采集摄像头、车牌、人员等非法或敏感信息
  - 所有数据仅存本机，不对外传输

运行方式:
    python server.py [--port 8090]
    浏览器打开 http://127.0.0.1:8090
"""

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "scout.db")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

for d in (DATA_DIR, UPLOAD_DIR, REPORT_DIR):
    os.makedirs(d, exist_ok=True)

APP_TITLE = "无线环境勘察系统 WireScout"
VERSION = "V1.0.1"

# OpenCellID 基站查询（可选）：通过环境变量 OPENCELLID_API_KEY 配置，未配置时自动跳过
OPENCELLID_API_KEY = os.environ.get("OPENCELLID_API_KEY", "").strip()


# ---------------------------------------------------------------- database
def db_init():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS datasets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, source TEXT, kind TEXT, rows INTEGER,
                created TEXT DEFAULT (datetime('now','localtime')))"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stations(
                ds_id INTEGER, name TEXT, ssid TEXT, lat REAL, lng REAL,
                signal REAL, channel TEXT, security TEXT, extra TEXT)"""
        )
        # 兼容旧表：缺 ssid 列时补充
        cols = [r[1] for r in conn.execute("PRAGMA table_info(stations)").fetchall()]
        if "ssid" not in cols:
            conn.execute("ALTER TABLE stations ADD COLUMN ssid TEXT")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cells(
                mcc INTEGER, mnc INTEGER, lac INTEGER, cellid INTEGER,
                lat REAL, lng REAL, rssi INTEGER, note TEXT,
                created TEXT DEFAULT (datetime('now','localtime')))"""
        )


# ---------------------------------------------------------------- netsh wifi
def _run(cmd, timeout=8):
    """执行系统命令，返回 stdout 文本（命令为白名单硬编码）。"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              creationflags=0x08000000 if os.name == "nt" else 0)
        return (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception as exc:
        return f"__ERROR__:{exc}"


def _norm(text):
    # 统一半角/全角冒号，便于解析
    return text.replace("：", ":")


def parse_netsh(text):
    """解析 netsh wlan show networks mode=bssid 输出为 AP 列表。"""
    text = _norm(text)
    ap, aps = {}, []
    in_ap = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if ap and in_ap:
                aps.append(ap)
                ap = {}
                in_ap = False
            continue
        lower = line.lower()
        if lower.startswith("ssid"):
            if ":" in line:
                key, val = line.split(":", 1)
                val = val.strip()
                if not in_ap and val:
                    ap = {"ssid": val}
                    in_ap = True
                elif in_ap:
                    ap.setdefault("ssid", val)
        elif in_ap:
            m = re.match(r"^(BSSID|Signal|Channel|Radio type|Basic rates|Other rates|Authentication|Encryption|信道|信号|频道|无线电类型|身份验证|加密)\s*[:：]\s*(.*)$", line, re.I)
            if m:
                k = m.group(1).lower()
                v = m.group(2).strip()
                mapping = {
                    "bssid": "bssid", "signal": "signal", "channel": "channel",
                    "radio type": "radio", "basic rates": "rates",
                    "other rates": "rates2", "authentication": "auth",
                    "encryption": "encryption",
                    "信号": "signal", "信道": "channel", "频道": "channel",
                    "无线电类型": "radio", "身份验证": "auth", "加密": "encryption",
                    "通道": "channel",
                }
                key = mapping.get(k, k)
                ap[key] = v
        elif lower.startswith("name"):
            pass
    if ap and in_ap:
        aps.append(ap)
    # 信号强度归一化
    for a in aps:
        sig = str(a.get("signal", "")).replace("%", "").strip()
        try:
            a["signal_pct"] = max(0, min(100, int(sig)))
        except Exception:
            a["signal_pct"] = None
    # 去重（同 BSSID 仅保留信号最强）
    seen, out = {}, []
    for a in aps:
        key = (a.get("bssid") or "").lower() or a.get("ssid", "")
        if key and key in seen:
            if (a.get("signal_pct") or 0) > (seen[key].get("signal_pct") or 0):
                out[out.index(seen[key])] = a
                seen[key] = a
        else:
            seen[key] = a
            out.append(a)
    return out


def wifi_scan():
    raw = ""
    if os.name == "nt":
        raw = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
    else:
        raw = _run(["nmcli", "-f", "SSID,BSSID,SIGNAL,CHAN,SECURITY", "dev", "wifi", "list"])
    if raw.startswith("_ERROR_"):
        return {"ok": False, "error": raw, "aps": []}
    aps = parse_netsh(raw)
    return {"ok": True, "aps": aps, "count": len(aps), "time": time.strftime("%Y-%m-%d %H:%M:%S")}


# ---------------------------------------------------------------- telemetry import
def sniff_columns(header):
    """自动识别列：lat/lng/ssid/name/security/channel 等。"""
    lat = lng = name = ssid = sec = ch = None
    for i, h in enumerate(header):
        hl = h.strip().lower()
        if lat is None and hl in ("lat", "latitude", "纬度", "lat度", "y"):
            lat = i
        elif lng is None and hl in ("lon", "lng", "long", "longitude", "经度", "x"):
            lng = i
        elif ssid is None and hl in ("ssid", "网络名", "essid"):
            ssid = i
        elif name is None and hl in ("name", "名称", "站点", "title", "站名"):
            name = i
        elif sec is None and hl in ("security", "auth", "加密", "认证"):
            sec = i
        elif ch is None and hl in ("channel", "信道", "频道"):
            ch = i
    return {"lat": lat, "lng": lng, "name": name, "ssid": ssid,
            "security": sec, "channel": ch}


def _to_float(v):
    try:
        return float(str(v).strip().replace(",", ""))
    except Exception:
        return None


def import_csv(name, raw_bytes):
    """导入 CSV（自动编码探测 + 列映射），返回统计。"""
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    if "�" in text[:2000]:
        try:
            text = raw_bytes.decode("gbk", errors="replace")
        except Exception:
            pass
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return {"ok": False, "error": "空文件"}
    header = [h.strip() for h in rows[0]]
    cols = sniff_columns(header)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO datasets(name, source, rows) VALUES(?,?,?)",
                           (os.path.basename(name), "csv", max(0, len(rows) - 1)))
        dsid = cur.lastrowid
        n = 0
        for r in rows[1:]:
            if len(r) < max((c or 0) for c in cols.values() if c is not None) + 1:
                continue
            lat = _to_float(r[cols["lat"]]) if cols["lat"] is not None else None
            lng = _to_float(r[cols["lng"]]) if cols["lng"] is not None else None
            if lat is None and lng is None:
                continue
            name = r[cols["name"]] if cols["name"] is not None and cols["name"] < len(r) else ""
            ssid = r[cols["ssid"]] if cols["ssid"] is not None and cols["ssid"] < len(r) else ""
            sec = r[cols["security"]] if cols["security"] is not None and cols["security"] < len(r) else ""
            ch = r[cols["channel"]] if cols["channel"] is not None and cols["channel"] < len(r) else ""
            conn.execute(
                "INSERT INTO stations(ds_id,name,lat,lng,ssid,security,channel) VALUES(?,?,?,?,?,?,?)",
                (dsid, name, lat, lng, ssid, sec, ch))
            n += 1
    return {"ok": True, "dataset_id": dsid, "imported": n}


def import_geojson(raw_bytes):
    """导入 GeoJSON 站点集（FeatureCollection 或单 Feature）。"""
    try:
        gj = json.loads(raw_bytes.decode("utf-8-sig"))
    except Exception as exc:
        return {"ok": False, "error": f"JSON 解析失败: {exc}"}
    feats = gj.get("features", []) if gj.get("type") == "FeatureCollection" else ([gj] if gj.get("type") == "Feature" else [])
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO datasets(name, source, rows) VALUES(?,?,?)",
                           ("geojson 导入", "geojson", len(feats)))
        dsid = cur.lastrowid
        n = 0
        for f in feats:
            geo = f.get("geometry") or {}
            coords = geo.get("coordinates")
            if geo.get("type") == "Point" and coords and len(coords) >= 2:
                lng, lat = coords[0], coords[1]
            else:
                continue
            props = f.get("properties") or {}
            conn.execute(
                "INSERT INTO stations(ds_id, name, lat, lng, ssid, security, channel) VALUES(?,?,?,?,?,?,?)",
                (dsid, props.get("name", ""), lat, lng, props.get("ssid", ""),
                 props.get("security", ""), str(props.get("channel", ""))))
            n += 1
    return {"ok": True, "rows": n}


def import_kml(raw_bytes):
    """导入 KML（简易 Placemark/Point 解析）。"""
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    marks = re.findall(r"<Placemark>(.*?)</Placemark>", text, re.S)
    rows_out = []
    for mk in marks:
        nm = re.search(r"<name>(.*?)</name>", mk, re.S)
        pt = re.search(r"<coordinates>\s*([0-9\.\-]+)\s*,\s*([0-9\.\-]+)", mk)
        if not pt:
            continue
        rows_out.append((nm.group(1).strip() if nm else "", float(pt.group(2)), float(pt.group(1))))
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("INSERT INTO datasets(name, source, rows) VALUES(?,?,?)",
                            ("kml 导入", "kml", len(rows_out)))
        dsid = cur.lastrowid
        for name, lat, lng in rows_out:
            conn.execute("INSERT INTO stations(ds_id, name, lat, lng) VALUES(?,?,?,?)",
                         (dsid, name, lat, lng))
    return {"ok": True, "rows": len(rows_out)}


# ---------------------------------------------------------------- cells query (optional)
OPENCELLID_KEY = os.environ.get("OPENCELLID_API_KEY", "")


def query_opencellid(lat, lng, radius=5, api_key=OPENCELLID_KEY):
    """通过 OpenCellID 公开接口查询区域基站（需用户自配 API Key，可选）。"""
    if not api_key or api_key == "your_opencellid_api_key":
        return {"ok": False, "reason": "未配置 OPENCELLID_API_KEY，跳过（基站数据为可选增强项）"}
    url = ("http://opencellid.org/cell/getInArea?key=%s&lat=%.5f&lon=%.5f&radius=%d&format=json&limit=100"
           % (api_key, lat, lng, int(radius * 1000)))
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    cells = []
    for c in data.get("cells", []):
        cells.append({
            "mcc": c.get("mcc"), "mnc": c.get("mnc"),
            "lac": c.get("lac"), "cellid": c.get("cellid"),
            "lat": c.get("lat"), "lng": c.get("lon"),
            "rssi": c.get("avg_signal"), "note": c.get("note", ""),
        })
    if cells:
        with sqlite3.connect(DB_PATH) as conn:
            for c in cells:
                conn.execute("INSERT INTO cells(mcc,mnc,lac,cellid,lat,lng,rssi,note) VALUES(?,?,?,?,?,?,?,?)",
                             (c["mcc"], c["mnc"], c["lac"], c["cellid"],
                              c["lat"], c["lng"], c["rssi"], c["note"]))
    return {"ok": True, "cells": cells, "count": len(cells)}


# ---------------------------------------------------------------- report
def build_report():
    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        dsc = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
        sec_rows = conn.execute("SELECT security, COUNT(*) FROM stations WHERE security<>'' GROUP BY security").fetchall()
        cells = conn.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
    wifi = wifi_scan()
    return {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wifi": {"count": wifi["count"] if wifi["ok"] else 0, "aps": wifi.get("aps", [])},
        "stations": total, "datasets": dsc, "cells": cells,
        "security_dist": [{"type": s or "未知", "count": n} for s, n in sec_rows],
    }


# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            self._send(404, {"ok": False, "error": "not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, {k: v[0] for k, v in parse_qs(u.query).items()}
        if p == "/" or p == "/index.html":
            self._send_file(os.path.join(BASE_DIR, "index.html"), "text/html; charset=utf-8")
        elif p == "/api/health":
            self._send(200, {"ok": True, "app": APP_TITLE, "version": VERSION,
                             "python": sys.version.split()[0], "os": os.name})
        elif p == "/api/wifi/scan":
            self._send(200, wifi_scan())
        elif p == "/api/datasets":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT id, name, source, rows, created FROM datasets ORDER BY id DESC").fetchall()
            self._send(200, {"ok": True, "datasets": [dict(zip(["id", "name", "source", "rows", "created"], r)) for r in rows]})
        elif p == "/api/stations":
            ds = q.get("dataset", "")
            with sqlite3.connect(DB_PATH) as conn:
                if ds and ds.isdigit():
                    rows = conn.execute("SELECT rowid,name,lat,lng,ssid,security,channel FROM stations WHERE ds_id=?", (int(ds),)).fetchall()
                else:
                    rows = conn.execute("SELECT rowid,name,lat,lng,ssid,security,channel FROM stations").fetchall()
            self._send(200, {"ok": True, "count": len(rows), "stations": [dict(zip(["id", "name", "lat", "lng", "ssid", "security", "channel"], r)) for r in rows]})
        elif p == "/api/report":
            self._send(200, build_report())
        elif p == "/api/cells/search":
            try:
                lat = float(q.get("lat", "0"))
                lng = float(q.get("lng", "0"))
                radius = float(q.get("radius", "5"))
            except ValueError:
                self._send(400, {"ok": False, "error": "lat/lng 参数非法"})
                return
            self._send(200, query_opencellid(lat, lng, radius, OPENCELLID_API_KEY))
        elif p == "/api/cells":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT mcc,mnc,lac,cellid,lat,lng,rssi,note,created FROM cells ORDER BY rowid DESC LIMIT 500").fetchall()
            self._send(200, {"ok": True, "count": len(rows), "cells": [dict(zip(["mcc", "mnc", "lac", "cellid", "lat", "lng", "rssi", "note", "created"], r)) for r in rows]})
        elif p == "/api/export":
            fmt = q.get("format", "geojson")
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT name, lat, lng, ssid, security, channel FROM stations").fetchall()
            if fmt == "geojson":
                feats = [{"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": [r[2], r[1]]},
                          "properties": {"name": r[0], "ssid": r[3], "security": r[4], "channel": r[5]}} for r in rows]
                self._send(200, {"type": "FeatureCollection", "features": feats})
            else:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["name", "lat", "lng", "ssid", "security", "channel"])
                w.writerows(rows)
                self._send(200, buf.getvalue(), "text/csv; charset=utf-8")
        else:
            self._send(404, {"ok": False, "error": "unknown api"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/import":
            length = int(self.headers.get("Content-Length", 0))
            if length > 50 * 1024 * 1024:
                self._send(413, {"ok": False, "error": "文件过大（上限 50MB）"})
                return
            raw = self.rfile.read(length) if length else b""
            ctype = self.headers.get("Content-Type", "")
            fname = ""
            # 简易 multipart 解析（单文件）
            if "multipart/form-data" in ctype:
                boundary = ctype.split("boundary=")[-1].strip().strip('"')
                parts = raw.split(("--" + boundary).encode())
                for part in parts:
                    if b"filename=" in part.split(b"\r\n\r\n", 1)[0]:
                        head, _, body = part.partition(b"\r\n\r\n")
                        m = re.search(rb'filename="([^"]+)"', head)
                        fname = m.group(1).decode("utf-8", "replace") if m else ""
                        raw = body
                        break
            else:
                fname = self.headers.get("X-Filename", "import.csv")
            if fname.lower().endswith(".geojson") or fname.lower().endswith(".json"):
                res = import_geojson(raw)
            elif fname.lower().endswith(".kml"):
                res = import_kml(raw)
            else:
                res = import_csv(fname or "import.csv", raw)
            self._send(200, {"ok": True, **res} if res.get("ok") else {"ok": False, "error": res.get("error", "导入失败")})
        else:
            self._send(404, {"ok": False, "error": "unknown api"})


def main():
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--port", type=int, default=8090)
    args = ap.parse_args()
    db_init()
    print("=" * 56)
    print("  无线环境勘察系统 WireScout %s" % VERSION)
    print("  本地服务: http://127.0.0.1:%d" % args.port)
    print("  Ctrl+C 退出")
    print("=" * 56)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")


if __name__ == "__main__":
    main()