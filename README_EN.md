
# WirelessScout - Wireless Survey & Simulation Assistant

A local wireless environment survey and simulation assistant: passive WiFi scanning, telemetry data import, regional base-station query, survey report generation, and map visualization. All data stays on-device; designed for enterprise intranets and large-event telecom assurance scenarios.

> Inspired by [SimART](https://github.com/guchuanv-alt/SimART) (an open-source all-scenario wireless communication and sensing research platform). This project is an original implementation, not a code copy.

## Features

- **WiFi survey**: passive scan of visible networks via system NIC (Windows `netsh` / Linux `nmcli`), parsing SSID / BSSID / signal / channel / auth / encryption
- **Telemetry import**: CSV (auto column mapping & encoding detection), GeoJSON, KML station data
- **Cell query (optional)**: OpenCellID public API, enable via `OPENCELLID_API_KEY` environment variable
- **Map visualization**: Leaflet station map (falls back to table view without external network)
- **Survey report**: AP count, security distribution, channel usage, signal quality, station stats
- **Data export**: GeoJSON / CSV for reuse in coverage simulation and planning tools

## Quick Start

Requires only Python 3.8+ standard library:

```bash
python server.py --port 8090
# open http://127.0.0.1:8090
```

Optional:

```bash
set OPENCELLID_API_KEY=your_key   # Windows; enables regional cell query
python server.py --port 8090
```

## API Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | service status |
| `/api/wifi/scan` | GET | survey visible WiFi |
| `/api/import` | POST | import CSV/GeoJSON/KML |
| `/api/datasets` | GET | dataset list |
| `/api/stations?dataset=<id>` | GET | station list |
| `/api/report` | GET | survey report |
| `/api/cells/search?lat=&lng=&radius=` | GET | query regional cells (optional) |
| `/api/export?format=csv\|geojson` | GET | export all stations |

## License

MIT License, Copyright (c) 2026 Hanfeng He. SimART is referenced only for conceptual inspiration; no source code is copied.