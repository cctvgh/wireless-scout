
# 无线勘察与仿真助手 API 参考

> 服务：WireScout（无线勘察与仿真助手）本地服务，默认 `http://127.0.0.1:8090`
> 协议：HTTP JSON；上传接口支持 multipart/form-data 与 `X-Filename` 头两种方式
> 所有接口均为只读勘察或本地数据操作，数据不出本机

## 快速速览

| Endpoint | Method | 用途 |
|----------|--------|------|
| `/api/health` | GET | 服务状态 |
| `/api/wifi/scan` | GET | 勘察本机可见 WiFi |
| `/api/import` | POST | 导入 CSV/GeoJSON/KML |
| `/api/datasets` | GET | 数据集列表 |
| `/api/stations?dataset=<id>` | GET | 站点列表（可按数据集过滤） |
| `/api/report` | GET | 勘察统计报告 |
| `/api/export?format=csv\|geojson` | GET | 导出全部站点 |
| `/api/cells` | GET | 本地已保存基站记录 |

---

## GET /api/health

服务健康检查。

```json
{"ok": true, "app": "无线环境勘察系统 WireScout", "version": "V1.0.1", "python": "3.12.13", "os": "nt"}
```

## GET /api/wifi/scan

被动勘察本机无线网卡可见网络。Windows 调用 `netsh wlan show networks mode=bssid`，Linux 调用 `nmcli dev wifi list`。

响应字段：

| 字段 | 说明 |
|------|------|
| `ok` | 是否成功 |
| `aps[]` | AP 列表，含 ssid/bssid/signal/signal_pct/channel/radio/auth/encryption |
| `count` | AP 数量 |
| `time` | 勘察时间 |

说明：

- `signal_pct` 为信号强度百分比（0-100），由 netsh 输出归一化
- 同 BSSID 去重，保留信号最强的一个
- 无无线网卡/被禁用时返回 `aps: []`，属正常现象

## POST /api/import

导入站点数据。支持 CSV（自动探测 UTF-8/GBK）、GeoJSON（FeatureCollection 或单 Feature）、KML（Placemark/Point）。

**方式一：multipart 上传**

```bash
curl -F "file=@sites.csv" http://127.0.0.1:8090/api/import
```

**方式二：X-Filename 头 + 原始字节**

```bash
curl -H "X-Filename: sites.geojson" --data-binary @sites.geojson http://127.0.0.1:8090/api/import
```

CSV 自动列映射（表头识别）：`lat/latitude/纬度`、`lng/lon/longitude/经度`、`ssid/网络名`、`name/名称/站点/站名`、`security/auth/加密/认证`、`channel/信道/频道`。

响应：

```json
{"ok": true, "dataset_id": 1, "imported": 12}
```

或 KML/GeoJSON 返回 `{"ok": true, "rows": 12}`。

## GET /api/datasets

已导入数据集列表（按时间倒序）。

```json
{"ok": true, "datasets": [{"id": 1, "name": "sites.csv", "source": "csv", "rows": 235, "created": "2026-09-15 10:00:00"}]}
```

## GET /api/stations?dataset=<id>

站点列表。`dataset` 缺省时返回全部站点。

```json
{"ok": true, "count": 235, "stations": [{"id": 1, "name": "Site-A", "lat": 22.941, "lng": 113.332, "ssid": "", "security": "WPA2", "channel": "6"}]}
```

## GET /api/report

勘察统计报告，用于汇报与报告生成。

```json
{
  "time": "2026-09-15 10:00:00",
  "wifi": {"count": 18, "aps": [...]},
  "stations": 235,
  "datasets": 3,
  "cells": 0,
  "security_dist": [{"type": "WPA2", "count": 200}, {"type": "未知", "count": 35}]
}
```

## GET /api/export?format=geojson|csv

导出全部站点。`geojson` 返回 FeatureCollection（Points，properties 含 name/ssid/security/channel）；`csv` 返回带表头 CSV。

## GET /api/cells/search?lat=&lng=&radius=

查询区域基站（OpenCellID 公开接口，可选功能）。

- 参数：`lat`（纬度，必填）、`lng`（经度，必填）、`radius`（公里，默认 5）
- 前置条件：以环境变量 `OPENCELLID_API_KEY` 配置 Key，如 `set OPENCELLID_API_KEY=xxx` 后启动服务
- 未配置时返回 `{"ok": false, "reason": "未配置 OPENCELLID_API_KEY，跳过（基站数据为可选增强项）"}`，不影响其他功能
- 查询成功后结果写入本地 `cells` 表，可通过 `/api/cells` 查看

## GET /api/cells

本地已保存的基站记录。未配置 `OPENCELLID_API_KEY` 时无数据，返回空列表。

---

## 错误与排查

| 现象 | 原因与处理 |
|------|-----------|
| 返回 `{"ok": false, "error": "JSON 解析失败"}` | GeoJSON 文件损坏或非 JSON |
| 导入 0 行 | 表头无法映射经纬度列；检查文件首行字段名 |
| `scan` 返回空列表 | 无无线网卡/无线禁用/虚拟机环境 |
| 端口占用 | `python server.py --port 8091` 换端口 |

## 安全说明

- 所有接口仅监听 `127.0.0.1`（本地回环）
- 仅被动勘察，无主动探测/攻击行为
- 上传数据仅写入本地 SQLite，不对外传输