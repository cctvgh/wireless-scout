---
name: wireless-scout
description: 无线勘察与信号覆盖助手（WireScout）：调用系统无线网卡被动勘察 WiFi 网络（SSID/信号/信道/加密），导入 CSV/GeoJSON/KML 站点遥测数据与 LTE/NR 路测数据（RSRP/RSRQ/SINR/PCI/小区，适配网优任我行/掌上优等路测 APP 导出，地图按 RSRP 分级着色），可选查询区域基站，一键生成勘察报告与地图可视化。零第三方依赖、数据全程不出本机，适合运营商网优、通信设计院与大型活动通信保障团队在内网/防火墙环境直接使用。触发词：无线勘察、WiFi扫描、扫网、信号覆盖、站点导入、路测数据、RSRP、网优、网优任我行、掌上优、基站查询、勘察报告、通信保障、活动保障无线勘察、WireScout、无线环境勘察、仿真辅助、站点分布。
name_cn: 无线勘察与信号覆盖助手
description_cn: 被动勘察本机可见 WiFi 网络（SSID/信号/信道/加密），导入站点遥测与 LTE/NR 路测数据（地图按 RSRP 分级着色），可选基站查询，一键生成勘察报告与地图。零依赖、内网可用、数据不出本机，面向网优与大型活动通信保障。
create_source: super-agent-skill-creator
---

# 无线勘察与信号覆盖助手 (WireScout)

## 概述

WireScout 是一个本地运行的无线环境勘察与仿真辅助工具：被动读取本机无线网卡可见的 WiFi 网络，支持将 CSV / GeoJSON / KML 站点数据导入本地库，生成地图与勘察报告。全部实现仅依赖 Python 标准库 + 原生 HTML/JS，适合企业内网（防火墙/VPN/堡垒机环境）直接运行，数据全程不出本机。

参考 SimART（全场景无线通信与感知仿真平台）的场景化勘察思路，本工具面向通信保障现场的**实勘数据采集与态势可视化**，可配合网络规划与覆盖评估使用。

能力总览：

| 能力 | 说明 |
|------|------|
| WiFi 勘察 | Windows 调用 `netsh wlan show networks mode=bssid`（只读），解析 SSID/BSSID/信号/信道/认证/加密；Linux 回退 `nmcli` 可见列表 |
| 遥测导入 | CSV（自动列映射 lat/lng/name/ssid/security/channel + LTE/NR 路测字段 rsrp/rsrq/sinr/pci/cell_id）、GeoJSON FeatureCollection、KML Placemark |
| 地图可视化 | Leaflet 站点分布地图（OSM 瓦片，内网无外网时可退化为列表视图）；LTE/NR 站点按 RSRP 分级着色（优/良/弱/差四档，右下角图例） |
| 基站查询（可选） | OpenCellID 公开接口，强制 HTTPS 加密调用，需以环境变量 OPENCELLID_API_KEY 配置 Key（不硬编码/不记录日志）；未配置时自动跳过，不影响主流程 |
| 勘察报告 | 汇总统计（AP 数量、加密分布、信道占用、信号质量、导入站点数、RSRP 分级分布） |
| 数据导出 | GeoJSON / CSV 一键导出（含 RSRP/RSRQ/SINR/PCI/小区 全部信号字段），可交至规划工具或仿真平台复用 |

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

### 部署环境说明

- 工具为绿色拷贝：仅需 `server.py` + `index.html` 两个文件 + Python 环境，无第三方依赖，可经 U 盘/共享目录自由拷贝到其他机器使用。
- 云电脑/虚拟机通常无实体无线网卡，WiFi 勘察返回空列表属正常，站点导入/地图/报告/导出均不受影响。推荐分工：实体笔记本（带无线网卡）现场勘察采集 → 数据文件传回云电脑汇总分析出报告。

## LTE/NR 路测数据支持（V1.2.0+）

除 WiFi 遥测外，支持导入 LTE/NR 蜂窝路测数据（「网优任我行」「掌上优」等路测 APP 导出的 CSV/GeoJSON）：

- CSV 表头自动识别 `RSRP/RSRQ/SINR/PCI/小区` 列（大小写/空格/下划线/连字符容错，如 `SS-RSRP`、`Cell ID`）；旧库启动时自动补列，无需重建数据库
- 地图站点按 RSRP 分级着色：≥ -70 dBm 优（绿）/ -90~-70 良（黄绿）/ -100~-90 弱（橙）/ < -100 差（红）/ 无 RSRP 灰；弹窗显示小区/PCI/RSRP/RSRQ/SINR
- 勘察报告新增 RSRP 分级分布统计；导出 CSV/GeoJSON 携带全部信号字段
- 定位边界：本工具是轻量勘察态势可视化层，DT/CQT 深度分析（吞吐率、邻区、导频污染等）仍需 Probe/Pioneer/ACP 等专业路测软件

字段映射、分级阈值与部署自检流程见 [references/lte-nr-import.md](references/lte-nr-import.md)；导入验证可用测试样例 [templates/lte_test.csv](templates/lte_test.csv)。

## 工作流程（LLM 执行指引）

### 1. 用户请求无线勘察

- 启动服务：`python <skill_dir>\assets\server.py --port 8090`（后台运行）。
- 调用 `GET /api/wifi/scan` 获取可见 AP 列表。
- 汇总输出：AP 总数、独立 SSID 数、开放网络数、信号 Top 列表；如返回 `aps:[]` 且服务正常，提示本机无无线网卡或权限受限。

### 2. 用户提供站点数据文件（CSV/GeoJSON/KML）

- 引导用户上传文件（可直接拖拽到界面，或提供本地路径由 Agent 代为调用 `POST /api/import`，multipart 或 `X-Filename` 头均可）。
- 导入成功后调用 `/api/datasets` 确认数据集与行数。
- 通过 `/api/stations?dataset=<id>` 校验数据解析正确性（经纬度/名称是否齐全；LTE/NR 路测数据另核对 rsrp/rsrq/sinr/pci/cell_id 是否入库）。

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
- **cells 表报错（旧版）**：V1.0.1 已修复 cells 表字段映射；V1.0.2 安全加固（强制 HTTPS / API Key 脱敏）；V1.2.0 新增 LTE/NR 路测字段并修复两个前端 bug（数据集下拉框引用了不存在的 `#mapDataset`、调用了不存在的 `renderStationTable()`，均会导致站点表格/地图不渲染）；若使用旧版 server.py/index.html，请重新复制。
- **LTE/NR 字段导入后为空**：确认 CSV 表头可被识别（列名对照见 references/lte-nr-import.md）；大小写/空格/下划线/连字符已容错，完全不同的命名需先改表头再导入。

## 合规红线

- 仅**被动勘察**本机可见信标，不做主动攻击、破解、注入、拒绝服务
- 不采集摄像头、车牌、人脸等敏感信息，不对接任何侦察/破解数据源
- 数据仅存本机 `data/` 目录，不对外传输；勘察结果用于网络运维、覆盖优化、活动保障等正当用途
- 外部数据源（OpenCellID）强制 HTTPS 加密调用，API Key 仅从环境变量读取，不硬编码/不写入日志/不输出完整 URL；代码内置 scheme 校验，非 `https://` 拒绝请求
- 本技能为独立原创实现，参考开源项目仅借鉴功能理念，不复制其代码