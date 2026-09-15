
# 数据源与字段说明

## 1. WiFi 勘察（netsh / nmcli）

- Windows: `netsh wlan show networks mode=bssid`（只读）。解析字段：SSID、BSSID、Signal(%)、Channel、Radio type、Authentication、Encryption。
- Linux: `nmcli -f SSID,BSSID,SIGNAL,CHAN,SECURITY dev wifi list`（回退方案）。
- 限制：勘察结果取决于本机无线网卡可见范围；无网卡/权限受限时返回空数组，属正常。
- 信号强度归一化为 0-100（signal_pct），同 BSSID 去重保留信号最强。

## 2. 遥测数据导入

### CSV
- 自动探测编码：优先 UTF-8(BOM)，失败回退 GBK（中文 Windows 导出常见）。
- 自动列映射（按列头名称识别，不区分大小写）：
  - 纬度: `lat` / `latitude` / `纬度` / `y`
  - 经度: `lon` / `lng` / `longitude` / `经度` / `x`
  - 名称: `name` / `title` / `名称` / `站点` / `站名`
  - SSID: `ssid` / `essid` / `网络名`
  - 加密: `security` / `auth` / `加密` / `认证`
  - 信道: `channel` / `信道` / `频道`
- 无经纬度的行会被跳过；经纬度必须有数值。

### GeoJSON
- 支持 `FeatureCollection` 与单个 `Feature`，仅取 `Point` 几何（`coordinates: [lng, lat]`）。
- 属性从 `properties` 读取：`name` / `ssid` / `security` / `channel`。

### KML
- 解析 `<Placemark>` 内 `<name>` + `<coordinates>lon,lat,alt</coordinates>`（取前两项）。

## 3. 基站查询（可选）

- 数据源：OpenCellID 公开接口 `http://opencellid.org/cell/getInArea`。
- 需要用户自行申请 Key，并以环境变量方式配置：`OPENCELLID_API_KEY=xxx python server.py --port 8090`。
- 页面/API 通过 `/api/cells/search?lat=&lng=&radius=`（radius 单位：公里）触发查询，结果写入本地 `cells` 表。
- 未配置时接口返回提示并跳过，不影响其他功能。

## 4. 存储与导出

- SQLite 数据库：`data/scout.db`（自动创建）。表：`datasets`（数据集元信息）、`stations`（站点）、`cells`（基站）。
- 上传文件存于 `data/uploads/`。
- 导出：GeoJSON（FeatureCollection）/ CSV（name,lat,lng,ssid,security,channel）。

## 5. 合规注意事项

- 本工具只做被动勘察与本地数据处理，不实施任何主动探测、破解或非法监听。
- 勘察数据建议用于：自有网络覆盖优化、活动保障无线环境评估、故障定位、行业分析。
- 引用本项目代码到其他系统时，保留数据本地化与合规红线章节。