
# 无线勘察与仿真助手 (WireScout)

一个本地运行的无线环境勘察与仿真辅助工具：被动勘察 WiFi 网络、导入站点遥测数据、查询区域基站、生成勘察报告与地图可视化。数据全程不出本机，适配企业内网与大型活动通信保障场景。

> 参考 [SimART](https://github.com/guchuanv-alt/SimART)（全场景无线通信与感知仿真平台）的场景化勘察理念独立开发，代码为原创实现。

## 功能特性

- **WiFi 勘察**：调用系统无线网卡被动勘察可见网络（Windows `netsh` / Linux `nmcli`），解析 SSID / BSSID / 信号 / 信道 / 认证 / 加密
- **遥测数据导入**：CSV（自动列映射与编码探测）、GeoJSON、KML 站点数据一键入库
- **基站查询（可选）**：OpenCellID 公开接口，环境变量配置 Key，未配置自动跳过
- **地图可视化**：Leaflet 站点分布地图（内网无外网时自动退化为列表视图）
- **勘察报告**：AP 数量、加密分布、信道占用、信号质量、站点统计汇总
- **数据导出**：GeoJSON / CSV 一键导出，可交至覆盖仿真与规划工具复用

## 快速开始

仅需 Python 3.8+ 标准库，无第三方依赖：

```bash
python server.py --port 8090
# 浏览器打开 http://127.0.0.1:8090
```

首次启动自动创建 `data/scout.db` 初始库。可选配置：

```bash
set OPENCELLID_API_KEY=your_key   # Windows；启用区域基站查询
python server.py --port 8090
```

## 目录结构

```
wireless-scout/
├── SKILL.md                  # TeleAgent 技能定义（技能市场可直接导入）
├── assets/
│   ├── server.py             # 本地勘察服务（Python 标准库）
│   └── index.html            # 前端界面（原生 HTML/JS）
└── references/
    ├── api_reference.md      # API 参考
    └── data-sources.md       # 数据源与字段说明
```

## API 概览

| Endpoint | Method | 用途 |
|----------|--------|------|
| `/api/health` | GET | 服务状态 |
| `/api/wifi/scan` | GET | 勘察本机可见 WiFi |
| `/api/import` | POST | 导入 CSV/GeoJSON/KML |
| `/api/datasets` | GET | 数据集列表 |
| `/api/stations?dataset=<id>` | GET | 站点列表 |
| `/api/report` | GET | 勘察统计报告 |
| `/api/cells/search?lat=&lng=&radius=` | GET | 查询区域基站（可选） |
| `/api/export?format=csv\|geojson` | GET | 导出全部站点 |

## 合规说明

- 仅被动勘察本机可见信标，无主动探测、破解、注入或拒绝服务行为
- 不采集摄像头、车牌、人脸等敏感信息
- 数据仅存本机，不对外传输；勘察结果用于网络运维、覆盖优化、活动保障等正当用途

## 许可

MIT License，Copyright (c) 2026 何汉锋。参考项目 SimART（全场景无线通信与感知仿真平台）仅借鉴功能理念，未复制其代码。

## 安装为 TeleAgent 技能

将 `wireless-scout.skill` 包导入 TeleAgent 技能市场即可；或直接使用 `skill/wireless-scout/` 目录。