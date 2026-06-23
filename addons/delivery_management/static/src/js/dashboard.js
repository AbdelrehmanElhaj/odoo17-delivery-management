/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
const TILE_URL    = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const POLL_MS     = 30_000;
// Default center: Riyadh
const DEFAULT_CENTER = [24.7136, 46.6753];

function loadLeaflet() {
    return new Promise((resolve) => {
        if (window.L) { resolve(); return; }
        if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
            const link = Object.assign(document.createElement("link"), {
                rel: "stylesheet", href: LEAFLET_CSS,
            });
            document.head.appendChild(link);
        }
        const script = Object.assign(document.createElement("script"), { src: LEAFLET_JS });
        script.onload = resolve;
        document.head.appendChild(script);
    });
}

export class DeliveryDashboard extends Component {

    setup() {
        this.rpc    = useService("rpc");
        this.mapEl  = useRef("map");
        this.state  = useState({ trips: [], loaded: false, vehicleCount: 0, inProgressCount: 0 });
        this._map     = null;
        this._markers = new Map();
        this._timer   = null;
        this._fitted  = false;

        onMounted(async () => {
            await loadLeaflet();
            this._initMap();
            await this._refresh();
            this._timer = setInterval(() => this._refresh(), POLL_MS);
        });

        onWillUnmount(() => {
            clearInterval(this._timer);
            if (this._map) this._map.remove();
        });
    }

    _initMap() {
        const L = window.L;
        this._map = L.map(this.mapEl.el, { center: DEFAULT_CENTER, zoom: 10 });
        L.tileLayer(TILE_URL, {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(this._map);
    }

    async _refresh() {
        try {
            const data = await this.rpc("/delivery/dashboard/data");
            if (!data || data.error) return;
            this.state.trips = data.trips || [];
            this.state.inProgressCount = this.state.trips.filter(t => t.state === "in_progress").length;
            this.state.vehicleCount = (data.vehicles || []).filter(v => v.lat && v.lng).length;
            this._updateMarkers(data.vehicles || []);
            this.state.loaded = true;
        } catch (_) { /* network blip — keep showing last data */ }
    }

    _updateMarkers(vehicles) {
        const L = window.L;
        const seen = new Set();

        for (const v of vehicles) {
            if (!v.lat || !v.lng) continue;
            seen.add(v.id);
            const latlng = [v.lat, v.lng];
            const popupHtml = this._popupHtml(v);

            if (this._markers.has(v.id)) {
                this._markers.get(v.id).setLatLng(latlng).setPopupContent(popupHtml);
            } else {
                const stateColor = v.trip_state === "in_progress" ? "#198754" : "#ffc107";
                const icon = L.divIcon({
                    className: "",
                    html: `<div style="background:${stateColor};color:#fff;padding:4px 8px;border-radius:4px;
                                font-size:12px;font-weight:700;white-space:nowrap;box-shadow:0 2px 4px rgba(0,0,0,.3)">
                               🚚 ${v.plate || v.name}
                           </div>`,
                    iconSize: null,
                    iconAnchor: [0, 0],
                });
                const marker = L.marker(latlng, { icon })
                    .bindPopup(popupHtml)
                    .addTo(this._map);
                this._markers.set(v.id, marker);
            }
        }

        for (const [id, marker] of this._markers) {
            if (!seen.has(id)) {
                marker.remove();
                this._markers.delete(id);
            }
        }

        if (!this._fitted && seen.size) {
            const latlngs = [...this._markers.values()].map(m => m.getLatLng());
            this._map.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40] });
            this._fitted = true;
        }
    }

    _popupHtml(v) {
        const rows = [
            `<strong>${v.plate || v.name}</strong>`,
            v.driver  ? `<div>👤 ${v.driver}</div>` : "",
            v.trip    ? `<div>📋 ${v.trip}</div>` : "",
            v.pending_stops ? `<div>📍 ${v.pending_stops} stop(s) left</div>` : "",
            v.gps_updated ? `<div style="color:#999;font-size:11px">Updated ${v.gps_updated}</div>` : "",
        ];
        return rows.filter(Boolean).join("");
    }
}

DeliveryDashboard.template = "delivery_management.Dashboard";

registry.category("actions").add("delivery_management.Dashboard", DeliveryDashboard);
