
# LTE/NR 路测数据导入参考（V1.2.0+）

WireScout 自 V1.2.0 起支持 LTE/NR 蜂窝路测数据导入与 RSRP 分级可视化，适配「网优任我行」「掌上优」等路测 APP 导出的 CSV/GeoJSON。WiFi 实时扫描能力不变；蜂窝信号无实时采集能力，只能通过数据导入。

## 数据库字段（stations 表新增）

旧库启动时自动 `ALTER TABLE` 补列，无需重建数据库：

| 字段 | 类型 | 说明 |
|------|------|------|
| rsrp | REAL | 参考信号接收功率（dBm） |
| rsrq | REAL | 参考信号接收质量（dB） |
| sinr | REAL | 信干噪比（dB） |
| pci | TEXT | 物理小区标识 |
| cell_id | TEXT | 小区标识（ECI/ECGI/TAC 等） |

## CSV 表头自动识别（sniff_columns）

表头先归一化（去首尾空格、转小写、去空格/下划线/连字符）再匹配，因此 `RSRP`、`rsrp`、`SS-RSRP`、`Cell ID`、`cell_id` 等写法均可识别：

| 字段 | 可识别表头（归一化后） |
|------|----------------------|
| lat | lat / latitude / 纬度 / y |
| lng | lon / lng / long / longitude / 经度 / x |
| rsrp | rsrp / ssrsrp / crsrsrp / ltersrp / nrrsrp / signal / signaldbm / 信号强度 / rsrpdb |
| rsrq | rsrq / ssrsrq / rsrqdb |
| sinr | sinr / sssinr / sinrdb / siner |
| pci | pci / pciid / 小区pci |
| cell_id | cell / cellid / eci / ecgi / tac / tcell / 小区 / 小区id / 小区标识 |

**坑位提示**：`signal`/`signaldbm`/`信号强度` 列会兜底映射到 rsrp。若导入的是 WiFi 遥测且该列为百分比信号（如 `85`），会被当作 RSRP=85 参与分级着色（显示为「优」），导入 WiFi 数据前建议核对或调整表头。

GeoJSON 导入从 Feature `properties` 读取 `rsrp/rsrq/sinr/pci/cell_id`（兼容 `SS-RSRP` 等大小写变体）；KML 仅解析 name+经纬度，不携带信号字段。

## RSRP 分级着色（index.html）

| RSRP 范围 | 等级 | 颜色 |
|-----------|------|------|
| ≥ -70 dBm | 优 | 绿 #10b981 |
| -90 ~ -70 dBm | 良 | 黄绿 #84cc16 |
| -100 ~ -90 dBm | 弱 | 橙 #f59e0b |
| < -100 dBm | 差 | 红 #ef4444 |
| 无 RSRP | — | 灰 #64748b |

- 地图右下角固定图例；circleMarker 弹窗显示 小区/PCI/RSRP/RSRQ/SINR
- 站点列表含 RSRP/RSRQ/SINR/PCI/小区 列
- 报告页输出 RSRP 分布条（`/api/report` 的 `rsrp_dist` 与 `rsrp_total`）

## 路测数据使用流程

1. 路测 APP（网优任我行/掌上优等）导出 CSV，确认含经纬度列 + 信号列
2. 「遥测导入」页签上传，或由 Agent 调 `POST /api/import`（`X-Filename` 头传文件名，或 multipart 均可）
3. 「站点地图」自动按 RSRP 分级着色；「勘察报告」查看 RSRP 分布
4. `GET /api/export?format=csv|geojson` 导出带全部信号字段的数据，交覆盖优化/仿真小组复用

## 部署自检流程（改造/升级后必做）

1. 复制 `assets/server.py`、`assets/index.html` 到临时目录再运行（勿直接在 assets 内跑，避免生成 `data/`、`__pycache__` 污染技能目录）
2. `python -m py_compile server.py` 确认语法
3. `python server.py --port 8099` 后台启动，`GET /api/health` 确认版本号
4. 用 `templates/lte_test.csv` 调 `POST /api/import` 导入（样例覆盖 优/良/弱/差 四档）
5. `GET /api/stations?dataset=<id>` 核对 rsrp/rsrq/sinr/pci/cell_id 解析正确
6. `GET /api/report` 核对 rsrp_dist 分级计数；浏览器打开首页确认无 JS 报错、图例与站点表格渲染正常
7. 测试完停止服务、清理临时目录

## 边界说明

- WireScout 是轻量勘察态势可视化层，不是专业路测分析平台；DT/CQT 深度分析（吞吐率、邻区分析、导频污染等）仍需 Probe/Pioneer/ACP 等专业软件
- 云电脑/虚拟机无无线网卡，WiFi 勘察返回空属正常；蜂窝路测数据导入不受影响