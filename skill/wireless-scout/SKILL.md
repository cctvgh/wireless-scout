---
name: wireless-scout
description: 无线勘察与仿真助手（WireScout）本地无线环境勘察与仿真辅助工具：调用系统无线网卡被动勘察 WiFi 网络（SSID/信号/信道/加密）、导入 CSV/GeoJSON/KML 站点遥测数据、查询区域基站、生成勘察报告与地图可视化；参考 SimART 全场景无线通信与感知仿真平台理念，辅助大型活动通信保障的无线环境勘察与站点覆盖评估。触发词：无线勘察、WiFi扫描、扫网、站点导入、基站查询、勘察报告、活动保障无线勘察、WireScout、无线环境勘察、仿真辅助、站点分布。
name_cn: 无线勘察与仿真助手
description_cn: 本地无线环境勘察与仿真辅助工具：WiFi勘察、站点遥测导入、基站查询、勘察报告与地图可视化，数据不出本机，适配活动保障勘察场景
create_source: super-agent-skill-creator
---

# 无线勘察与仿真助手 (WireScout)

## 概述

WireScout 是一个本地运行的无线环境勘察与仿真辅助工具：被动读取本机无线网卡可见的 WiFi 网络，支持将 CSV / GeoJSON / KML 站点数据导入本地库，生成地图与勘察报告。全部实现仅依赖 Python 标准库 + 原生 HTML/JS，适合企业内网（防火墙/VPN/堡垒机环境）直接运行，数据全程不出本机。

参考 SimART（全场景无线通信与感知仿真平台）的场景化勘察思路，本工具面向通信保障现场的**实勘数据采集与态势可视化**，可配合网络规划与覆盖评估使用。

能力总览：

| 能力 | 说明 |
|------|------|
| WiFi 勘察 | Windows 调用 `netsh wlan show networks mode=bssid`（只读），解析 SSID/BSSID/信号/信道/认证/加密；Linux 回退 `nmcli` 可见列表 |
| 遥测导入 | CSV（自动列映射 lat/lng/name/ssid/security/channel）、GeoJSON FeatureCollection、KML Placemark |
| 地图可视化 | Leaflet 站点分布地图（OSM 瓦片，内网无外网时可退化为列表视图） |
| 基站查询（可选） | OpenCellID 公开接口，需以环境变量 OPENCELLID_API_KEY 配置 Key；未配置时自动跳过，不影响主流程 |
| 勘察报告 | 汇总统计（AP 数量、加密分布、信道占用、信号质量、导入站点数） |
| 数据导出 | GeoJSON / CSV 一键导出，可交至规划工具或仿真平台复用 |

## 快速部署

1. 创建项目目录并复制资产：

```
mkdir D:\WireScout && cd D:\WireScout
copy <skill_dir>\assets\server.py .
copy <skill_dir>\assets\index.html .
```

2. 启动（Windows 直接命令行，无需第三方依赖）：

```
python server.py --port 8090
```

首次启动自动创建 `data/scout.db`（SQLite 初始库）与 `data/uploads`、`reports` 目录。

3. 浏览器打开 `http://127.0.0.1:8090` 进入主界面（四个页签：WiFi 勘察 / 站点地图 / 遥测导入 / 勘察报告）。

## 工作流程（LLM 执行指引）

### 1. 用户请求无线勘察

- 启动服务：`python <skill_dir>\assets\server.py --port 8090`（后台运行）。
- 调用 `GET /api/wifi/scan` 获取可见 AP 列表。
- 汇总输出：AP 总数、独立 SSID 数、开放网络数、信号 Top 列表；如返回 `aps:[]` 且服务正常，提示本机无无线网卡或权限受限。

### 2. 用户提供站点数据文件（CSV/GeoJSON/KML）

- 引导用户上传文件（可直接拖拽到界面，或提供本地路径由 Agent 代为调用 `POST /api/import`，multipart 或 `X-Filename` 头均可）。
- 导入成功后调用 `/api/datasets` 确认数据集与行数。
- 通过 `/api/stations?dataset=<id>` 校验数据解析正确性（经纬度/名称是否齐全）。

### 3. 生成勘察报告

- 调用 `/api/report`，将统计结果整理为结构化小结（可见 AP、导入站点、数据集、基站记录、加密分布）。
- 导出站点：`/api/export?format=geojson`（用于地图工具）或 `format=csv`（用于表格）。

### 4. 活动保障场景

大型活动（赛事/展会/应急）保障时：导入现场测试站点与 AP 遥测 → 地图可视化定位盲区 → 生成勘察报告 → 导出 GeoJSON 供覆盖仿真与优化小组复用。输出前按用户偏好整理为通信保障文档（政企协同措辞、分区域小结）。

## 关键 API

| Endpoint | Method | 用途 |
|----------|--------|------|
| `/api/health` | GET | 服务状态（应用名/版本/Python/OS） |
| `/api/wifi/scan` | GET | 勘察本机可见 WiFi（netsh/nmcli 解析） |
| `/api/import` | POST | 上传 CSV/GeoJSON/KML（multipart 或 X-Filename 头） |
| `/api/datasets` | GET | 已导入数据集列表 |
| `/api/stations?dataset=<id>` | GET | 站点列表（可按数据集过滤） |
| `/api/report` | GET | 勘察统计报告 |
| `/api/export?format=csv\|geojson` | GET | 导出全部站点 |
| `/api/cells/search?lat=&lng=&radius=` | GET | 查询区域基站（可选，需环境变量 OPENCELLID_API_KEY） |
| `/api/cells` | GET | 本地已保存基站记录 |

完整字段与示例见 [references/api_reference.md](references/api_reference.md)。

## 排查指引

- **扫描返回空列表**：本机无无线网卡、无线被禁用或驱动权限受限。检查 `netsh wlan show interfaces`；虚拟机/服务器环境属正常现象。
- **地图空白**：OSM 瓦片需外网；内网环境会自动保留站点列表表格，地图区域显示提示，不影响数据。
- **导入乱码**：CSV 自动探测 UTF-8/GBK 编码；中文 Excel 另存时优先 UTF-8。
- **端口被占用**：`--port` 换端口（如 8091），并同步更新浏览器地址。
- **cells 表报错（旧版）**：V1.0.1 已修复 cells 表字段映射；若使用旧版 server.py，请重新复制。

## 合规红线

- 仅**被动勘察**本机可见信标，不做主动攻击、破解、注入、拒绝服务
- 不采集摄像头、车牌、人脸等敏感信息，不对接任何侦察/破解数据源
- 数据仅存本机 `data/` 目录，不对外传输；勘察结果用于网络运维、覆盖优化、活动保障等正当用途
- 本技能为独立原创实现，参考开源项目仅借鉴功能理念，不复制其代码