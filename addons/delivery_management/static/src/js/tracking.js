/**
 * Delivery Management — Customer Tracking Page JS
 *
 * Polls /delivery/track/<token>/poll every 60 seconds and updates:
 *  - GPS marker on the map (Leaflet + OpenStreetMap, no API key required)
 *  - ETA display
 *  - Stops remaining count
 *  - GPS status badge
 */

(function () {
    'use strict';

    if (typeof window.DMS === 'undefined') return;  // only run on tracking page

    const POLL_INTERVAL_MS = 60_000;
    const DMS = window.DMS;

    let map = null;
    let marker = null;

    // ── Leaflet map init ───────────────────────────────────────────────────

    function initMap(lat, lng) {
        if (!document.getElementById('dms-map')) return;
        if (typeof L === 'undefined') {
            loadLeaflet(() => renderMap(lat, lng));
        } else {
            renderMap(lat, lng);
        }
    }

    function loadLeaflet(cb) {
        // Load Leaflet CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);

        // Load Leaflet JS
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.onload = cb;
        document.head.appendChild(script);
    }

    function renderMap(lat, lng) {
        const el = document.getElementById('dms-map');
        if (!el || map) return;

        map = L.map('dms-map').setView([lat, lng], 14);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(map);

        const truckIcon = L.icon({
            iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
        });

        marker = L.marker([lat, lng], { icon: truckIcon })
            .addTo(map)
            .bindPopup('Delivery vehicle');

        // Swap the offline placeholder for the actual map
        const offline = document.querySelector('.dms-map-offline');
        if (offline) offline.style.display = 'none';
    }

    function moveMarker(lat, lng) {
        if (!map) {
            initMap(lat, lng);
            return;
        }
        if (marker) {
            marker.setLatLng([lat, lng]);
            map.panTo([lat, lng]);
        }
    }

    // ── UI helpers ─────────────────────────────────────────────────────────

    function setGpsStatus(live) {
        const badge = document.getElementById('dms-gps-status');
        if (!badge) return;
        if (live) {
            badge.className = 'dms-gps-badge badge bg-success live';
            badge.innerHTML = DMS.isRtl
                ? '<i class="fa fa-circle"></i> مباشر'
                : '<i class="fa fa-circle"></i> Live';
        } else {
            badge.className = 'dms-gps-badge badge bg-secondary';
            badge.innerHTML = DMS.isRtl
                ? '<i class="fa fa-circle-o"></i> في انتظار الإشارة'
                : '<i class="fa fa-circle-o"></i> Awaiting signal';
        }
    }

    function updateEta(isoString) {
        const el = document.getElementById('dms-eta-display');
        if (!el) return;
        if (!isoString) { el.textContent = '—'; return; }
        const d = new Date(isoString);
        el.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function updateStopsRemaining(count) {
        const el = document.getElementById('dms-stops-remaining');
        if (!el) return;
        el.textContent = DMS.isRtl
            ? `${count} محطة متبقية`
            : `${count} stop(s) remaining`;
    }

    function updateLastUpdated(isoString) {
        const el = document.getElementById('dms-updated-time');
        if (!el || !isoString) return;
        const d = new Date(isoString);
        el.textContent = d.toLocaleTimeString();
    }

    // ── Polling ────────────────────────────────────────────────────────────

    async function poll() {
        try {
            const res = await fetch(DMS.pollUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            if (!res.ok) return;
            const json = await res.json();
            const data = json.result;
            if (!data || data.error) return;

            if (data.lat && data.lng) {
                moveMarker(data.lat, data.lng);
                setGpsStatus(true);
                updateLastUpdated(data.gps_updated);
            } else {
                setGpsStatus(false);
            }

            updateEta(data.eta);
            updateStopsRemaining(data.stops_remaining);

            // Auto-refresh page if order completed/failed
            if (['done', 'failed'].includes(data.state) && DMS.state !== data.state) {
                location.reload();
            }
            DMS.state = data.state;
        } catch (_) {
            // network error — silently retry next cycle
        }
    }

    // ── Boot ───────────────────────────────────────────────────────────────

    function boot() {
        if (DMS.lat && DMS.lng) {
            initMap(DMS.lat, DMS.lng);
            setGpsStatus(true);
        }
        poll();
        setInterval(poll, POLL_INTERVAL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
