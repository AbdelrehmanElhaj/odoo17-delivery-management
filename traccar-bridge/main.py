"""
Traccar → Odoo GPS Bridge
=========================
Receives position updates from Traccar via HTTP webhook and pushes them
to Odoo via XML-RPC.

Environment variables:
  ODOO_URL        Odoo base URL (default: http://web:8069)
  ODOO_DB         Database name (default: DeliveryDemo)
  ODOO_USER       Odoo login    (default: admin)
  ODOO_PASS       Odoo password (default: admin)
  WEBHOOK_SECRET  Shared secret sent in X-Api-Key header by Traccar
"""
import logging
import os
import xmlrpc.client
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request

log = logging.getLogger("traccar_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Traccar → Odoo GPS Bridge", version="2.0.0")

ODOO_URL       = os.getenv("ODOO_URL",       "http://web:8069")
ODOO_DB        = os.getenv("ODOO_DB",        "DeliveryDemo")
ODOO_USER      = os.getenv("ODOO_USER",      "admin")
ODOO_PASS      = os.getenv("ODOO_PASS",      "admin")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")

_uid_cache: Optional[int] = None


def _odoo_uid() -> int:
    global _uid_cache
    if _uid_cache is None:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
        if not uid:
            raise RuntimeError("Odoo authentication failed — check ODOO_USER / ODOO_PASS")
        _uid_cache = uid
        log.info("Authenticated as Odoo uid=%s", uid)
    return _uid_cache


def _push_gps(device_id: str, lat: float, lng: float) -> dict:
    uid = _odoo_uid()
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    result = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        "delivery.vehicle", "update_gps_position",
        [],
        {"device_id": device_id, "lat": lat, "lng": lng},
    )
    return result


def _reset_uid():
    global _uid_cache
    _uid_cache = None


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Traccar webhook ────────────────────────────────────────────────────────────

@app.post("/webhook")
async def traccar_webhook(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
):
    """
    Receives position events from Traccar via forward.url (traccar.xml).
    Traccar sends a flat JSON position object for every GPS update.

    traccar.xml:
        <entry key="forward.enable">true</entry>
        <entry key="forward.url">http://traccar-bridge:8000/webhook</entry>
        <entry key="forward.header.X-Api-Key">WEBHOOK_SECRET</entry>
    """
    if x_api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()

    # Traccar forward payload is a flat position object:
    # { "deviceId": 1, "id": ..., "latitude": ..., "longitude": ..., "deviceName": "...", "uniqueId": "..." }
    # Notification payload has nested device/position/event dicts.
    if isinstance(body, dict):
        # Flat forward payload
        if "latitude" in body and "longitude" in body:
            device_id = body.get("uniqueId") or str(body.get("deviceId", ""))
            lat = body.get("latitude")
            lng = body.get("longitude")
        # Nested notification payload (legacy / manual setup)
        elif "position" in body and "device" in body:
            pos = body["position"]
            dev = body["device"]
            device_id = dev.get("uniqueId") or str(dev.get("id", ""))
            lat = pos.get("latitude")
            lng = pos.get("longitude")
        else:
            return {"status": "ignored", "reason": "unrecognised payload shape"}
    else:
        return {"status": "ignored", "reason": "expected JSON object"}

    if not device_id or lat is None or lng is None:
        return {"status": "ignored", "reason": "missing device_id / lat / lng"}

    log.info("GPS update: device=%s lat=%.6f lng=%.6f", device_id, lat, lng)
    try:
        result = _push_gps(device_id, lat, lng)
        return {"status": "ok", "odoo": result}
    except Exception as exc:
        log.error("Odoo push failed: %s", exc)
        _reset_uid()
        raise HTTPException(status_code=502, detail=str(exc))


