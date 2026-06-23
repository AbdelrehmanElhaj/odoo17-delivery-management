# Delivery Management — Odoo 17

Custom Odoo 17 module for truck dispatch, real-time GPS tracking, and proof-of-delivery. Built for PropTech SA.

**Live demo:** https://dms.hdrelhaj.com  
**Module version:** 17.0.2.0.0

---

## Overview

Replaces spreadsheet-based truck dispatch with a fully integrated Odoo module. Drivers use a mobile PWA, customers get a live tracking link, and managers watch a real-time map dashboard.

## Architecture

```
Traccar Client app (driver phone)
        │
        ▼
traccar.hdrelhaj.com (dms-traccar)
        │ webhook (X-Api-Key)
        ▼
gps.hdrelhaj.com (dms-traccar-bridge)
        │ XML-RPC
        ▼
Odoo 17 (dms-odoo)
delivery.vehicle.update_gps_position()
        │
ir.cron → OSRM ETA engine
        │
Customer tracking page (60s poll)
```

## Features

- **Dispatch board** — create trips, assign drivers and vehicles, sequence stops
- **Live map dashboard** — OWL component, Leaflet/OSM, 30s auto-refresh, trip sidebar
- **Driver PWA** — Odoo portal `/my/deliveries`, Navigate button (Google Maps deep link), offline banner, Arabic RTL, photo upload
- **Customer tracking** — public page `/delivery/track/<token>`, Leaflet map, 60s auto-poll, no login required
- **GPS pipeline** — Traccar Client → Traccar server → FastAPI bridge → Odoo XML-RPC → ETA via OSRM
- **Proof-of-delivery** — photo upload per stop from the driver's phone
- **Tracking email** — sent automatically on order confirmation with a unique tracking link
- **OSRM ETA engine** — cron-driven chained ETA calculation across all active trip stops

## Data Models

| Model | Purpose |
|---|---|
| `delivery.vehicle` | Truck registry with GPS fields (`last_lat`, `last_lng`, `traccar_device_id`) |
| `delivery.driver` | Driver profile linked to `res.users` |
| `delivery.order` | Individual delivery/pickup linked to `sale.order`; unique `tracking_token` |
| `delivery.trip` | Groups orders into one dispatched run (1 vehicle, 1 driver) |
| `delivery.stop` | Address stop within a trip (sequence, status, ETA) |
| `delivery.photo` | Proof-of-delivery photo per stop |

## Stack

| Component | Technology |
|---|---|
| ERP | Odoo 17 Community (`odoo:17.0`) |
| Database | PostgreSQL 15 |
| Reverse proxy | Nginx (external Docker network `web`) |
| GPS bridge | FastAPI (`traccar-bridge/`) |
| GPS server | Traccar (`traccar.hdrelhaj.com`) |
| Maps | Leaflet + OpenStreetMap |
| ETA routing | OSRM (`router.project-osrm.org`) |
| SSL | Let's Encrypt (via `nginx-proxy` + `acme-companion`) |

## Services (Docker Compose)

| Container | Image | Purpose |
|---|---|---|
| `dms-db` | `postgres:15` | Odoo database |
| `dms-odoo` | `odoo17-delivery:latest` | Odoo application |
| `dms-traccar` | `traccar/traccar:latest` | GPS server |
| `dms-traccar-bridge` | built from `./traccar-bridge` | FastAPI GPS → Odoo bridge |

## Deployment

### Prerequisites

- Docker + Docker Compose
- External Docker network named `web` (shared with `nginx-proxy` + `acme-companion`)

```bash
docker network create web
```

### Start

```bash
docker compose up -d
```

### Install the module

1. Open https://dms.hdrelhaj.com
2. Go to **Settings → Apps → Update Apps List**
3. Search for **Delivery Management** and install

### Update after code changes

```bash
docker compose restart web
# then in Odoo: Settings → Technical → Update Module
```

## GPS Setup

GPS tracking uses **Traccar only**. Drivers install the Traccar Client app; positions flow to Traccar, then via webhook to the bridge, then to Odoo.

Traccar runs at `traccar.hdrelhaj.com` behind nginx (HTTPS, port 443). The device protocol is proxied through nginx — **do not use port 5055**.

**Traccar Client app settings (driver's phone):**

| Field | Value |
|---|---|
| Server URL | `https://traccar.hdrelhaj.com` |
| Port | `443` |
| Device Identifier | must match the vehicle's **Traccar Device ID** in Odoo |

**Wiring a new driver:**

1. Log in to `traccar.hdrelhaj.com` → **Devices → Add** — set a name and unique Identifier (e.g. `nuha-001`)
2. In Odoo → **Delivery → Configuration → Vehicles → [vehicle]** → set **Traccar Device ID** to the same Identifier → Save
3. Install Traccar Client on the driver's phone and enter the settings above

Traccar forwards every position to the bridge via webhook (configured in `traccar/traccar.xml`):
- `forward.url` → `http://traccar-bridge:8000/webhook`
- `forward.header.X-Api-Key` → your `WEBHOOK_SECRET`

## Environment Variables (traccar-bridge)

| Variable | Default | Description |
|---|---|---|
| `ODOO_URL` | `http://web:8069` | Odoo base URL |
| `ODOO_DB` | `DeliveryDemo` | Database name |
| `ODOO_USER` | `admin` | Odoo login |
| `ODOO_PASS` | `admin` | Odoo password |
| `WEBHOOK_SECRET` | `change-me-in-production` | Shared secret for Traccar webhook |

## Module Structure

```
addons/delivery_management/
├── models/
│   ├── delivery_vehicle.py      # GPS fields + update_gps_position()
│   ├── delivery_driver.py
│   ├── delivery_order.py        # tracking_token, confirm email
│   ├── delivery_trip.py         # OSRM ETA cron
│   ├── delivery_stop.py
│   └── delivery_photo.py
├── controllers/
│   ├── portal.py                # /delivery/track/<token>, /my/deliveries
│   └── dashboard.py             # /delivery/dashboard/data (JSON)
├── wizard/
│   └── create_delivery_wizard.py
├── templates/
│   ├── portal_tracking.xml      # Customer tracking page
│   └── portal_my_deliveries.xml # Driver PWA
├── static/src/
│   ├── js/dashboard.js          # OWL live map component
│   ├── js/tracking.js           # Customer tracking page JS
│   └── xml/dashboard.xml        # OWL template
├── views/                       # All backend views
├── data/
│   ├── cron.xml                 # ETA cron job
│   ├── mail_template.xml        # Tracking link email
│   └── sequences.xml
└── security/
```

## Odoo 17 Notes

- Use `<tree>` not `<list>` for list views; use `tree,form` in `view_mode`
- OWL import path: `@web/core/utils/hooks` (not `@web/hooks`)
- After JS/XML asset changes: delete `web.assets_web.min.js` from `ir_attachment`, restart Odoo, hard-refresh browser
- Admin group changes require logout + re-login

## License

LGPL-3

## Author

Abdelrehman Elhaj — [PropTech SA](https://proptech.sa)
