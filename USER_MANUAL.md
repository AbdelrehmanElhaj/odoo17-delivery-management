# Delivery Management — User Manual

**System URL:** https://dms.hdrelhaj.com  
**Version:** 17.0.2.0.0

---

## Roles

| Role | Who | Access |
|---|---|---|
| **Manager** | Dispatch staff, operations | Full Delivery menu — trips, orders, vehicles, drivers, live map |
| **Driver** | Truck drivers | Portal only — `/my/deliveries` on their phone |
| **Customer** | End recipients | Public tracking page — no login required |

---

## Manager Guide

### 1. Initial Setup

#### Add a Vehicle

**Delivery → Configuration → Vehicles → New**

| Field | Description |
|---|---|
| Name | Truck name (e.g. `Truck-001`) |
| License Plate | Required |
| Capacity (kg) | Optional, for reference |
| Traccar Device ID | Must match the identifier registered in Traccar — used to link GPS position to this vehicle |

#### Add a Driver

**Delivery → Configuration → Drivers → New**

| Field | Description |
|---|---|
| Name | Driver's full name |
| User | Link to an Odoo user account — the driver logs in to the portal with these credentials |
| Vehicle | Assign a default vehicle |
| Phone | Optional |

> The driver must have an Odoo portal/user account. Go to **Settings → Users → New** to create one if needed, then link it here.

---

### 2. Creating a Delivery Order

There are two ways to create a delivery order.

#### Option A — From a Sales Order (recommended)

1. Open any confirmed Sales Order
2. Click the **Create Delivery** button in the top bar
3. Fill in the wizard:
   - **Delivery Address** — auto-filled from the sales order, can be changed
   - **Mode** — Delivery or Pickup
   - **Scheduled Date** — when the delivery should happen
4. Click **Create** — the order is created in **Confirmed** state and a tracking email is sent to the customer automatically

#### Option B — Directly

**Delivery → Dispatch → Delivery Orders → New**

Fill in Customer, Mode, Scheduled Date, and optionally link a Sales Order. Click **Confirm** to send the tracking email.

##### Order States

```
Draft → Confirmed → In Progress → Done
                              ↘ Failed
```

| State | Meaning |
|---|---|
| Draft | Created, not yet sent |
| Confirmed | Tracking email sent to customer |
| In Progress | Trip has started |
| Done | All stops completed |
| Failed | Delivery could not be completed |

---

### 3. Creating and Dispatching a Trip

A trip groups one or more delivery orders into a single run for one driver and vehicle.

**Delivery → Dispatch → Trips → New**

#### Step 1 — Fill trip details

| Field | Description |
|---|---|
| Vehicle | Select the truck |
| Driver | Select the driver |
| Scheduled Date | Planned departure time |

#### Step 2 — Add Stops

In the **Stops** tab, add each address stop:

| Field | Description |
|---|---|
| Sequence | Order of stops (10, 20, 30…) — drag to reorder |
| Delivery Address | Customer address (auto-fills coordinates from the contact record) |
| Delivery Order | Link to the delivery order for this stop |
| Notes | Instructions for the driver at this stop |

> Make sure the customer contact has GPS coordinates set (**Contacts → [customer] → Geo-locate**), otherwise the ETA engine cannot calculate arrival times.

#### Step 3 — Dispatch

Click **Dispatch** — this:
- Sets the trip to **Dispatched** state
- Confirms all linked delivery orders (tracking emails sent)
- Makes the trip visible to the driver in their portal

#### Step 4 — Start

When the driver departs, click **Start** — sets trip to **In Progress** and records actual start time. The OSRM ETA engine begins calculating arrival times every few minutes.

#### Trip States

```
Draft → Dispatched → In Progress → Done
                              ↘ Cancelled
```

---

### 4. Live Map Dashboard

**Delivery → Live Map**

Shows all active vehicles on an OpenStreetMap map with:
- Real-time truck positions (auto-refreshes every 30 seconds)
- Trip sidebar listing active trips, driver, vehicle, and pending stop count
- Click a trip in the sidebar to highlight its vehicle on the map

> Vehicle positions only update if the driver's GPS app is running and sending data. The timestamp of the last GPS update is shown on each vehicle marker.

---

### 5. Monitoring Stops

**Delivery → Dispatch → Trips → [open a trip] → Stops tab**

Each stop shows:
- Current status (Pending / Arrived / Done / Failed)
- ETA (auto-calculated, updates every few minutes while in progress)
- Actual arrival time (set by the driver)
- Proof-of-delivery photos uploaded by the driver

You can manually override a stop's status using the action buttons on each stop row.

---

## Driver Guide

Drivers access the system from their phone browser — no app download required.

### Accessing the Portal

1. Open `https://dms.hdrelhaj.com/my/deliveries` on your phone
2. Log in with your Odoo username and password
3. You will see all trips assigned to you today

> **Tip:** Add the page to your home screen (Safari → Share → Add to Home Screen / Chrome → menu → Add to Home Screen) for quick access like a native app.

### Your Delivery List

Each trip shows as a card with all its stops listed in sequence order. For each stop you can see:
- Customer name and address
- ETA (if calculated)
- Any special notes from the dispatcher
- Current status badge

### Working a Stop

Follow this sequence for each stop:

#### 1. Navigate
Tap the **Navigate** button — opens Google Maps (or your phone's default maps app) with the destination pre-loaded.

#### 2. Mark Arrived
When you reach the address, tap **Arrived**. This records your actual arrival time.

#### 3. Upload Photo (optional but recommended)
While in Arrived status, use the camera button to take a proof-of-delivery photo. The photo is saved against this stop in Odoo.

#### 4. Complete the Stop
- Tap **Done** if the delivery was successful
- Tap **Failed** if the delivery could not be completed (customer absent, wrong address, etc.)

> Completing the last stop on a delivery order automatically marks that order as Done.

### Offline Mode

If you lose internet connection, a warning banner appears at the top:
> *"You are offline. Stop actions will sync when connection is restored."*

The page will continue to display your stops. Reconnect to resume syncing.

### GPS Tracking

Your location is shared with the office through the **Traccar Client** app — this runs separately in the background and does not affect this portal page.

**Traccar Client app settings:**

| Field | Value |
|---|---|
| Server URL | `https://traccar.hdrelhaj.com` |
| Port | `443` |
| Device Identifier | Provided by your manager |

Keep the Traccar Client app running while on a trip so the office can see your position on the live map.

---

## Customer Guide

### Receiving the Tracking Link

When your delivery is confirmed, you receive an email with a personal tracking link. The link looks like:

```
https://dms.hdrelhaj.com/delivery/track/xxxxxxxxxxxxxxxx
```

No login or account is required.

### Tracking Page

The tracking page shows:
- Current status of your delivery
- A live map with the driver's current position
- Estimated arrival time (updates automatically every 60 seconds)
- Delivery address pin

The page refreshes automatically — no need to reload manually.

---

## GPS Setup for New Drivers (Manager Reference)

### Traccar (current setup)

1. Log in to `https://traccar.hdrelhaj.com`
2. Go to **Devices → Add**
3. Set a **Name** (driver's name) and a unique **Identifier** (e.g. `nuha-001`)
4. In Odoo → **Delivery → Configuration → Vehicles → [vehicle]** → set **Traccar Device ID** to the same identifier → **Save**
5. Give the driver the Traccar Client app settings above

**Test the link:**
```bash
curl "https://gps.hdrelhaj.com/osmand?id=nuha-001&lat=24.7136&lon=46.6753&timestamp=1234567890"
# Expected: {"status":"ok","odoo":{"success":true,"vehicle_id":...}}
```

### OsmAnd (alternative, no Traccar app needed)

Configure OsmAnd GPS Tracker → Online tracking:
```
https://gps.hdrelhaj.com/osmand?id={deviceid}&lat={0}&lon={1}&timestamp={2}
```
Where `{deviceid}` matches the vehicle's **Traccar Device ID** in Odoo.

---

## Quick Reference

### Manager Daily Workflow

```
1. Create delivery orders (from Sales Orders or manually)
2. Create a trip → add stops in sequence → Dispatch
3. Monitor drivers on Live Map
4. Check stop statuses in the Stops tab
```

### Driver Daily Workflow

```
1. Open dms.hdrelhaj.com/my/deliveries
2. Start Traccar Client app
3. For each stop: Navigate → Arrived → (Photo) → Done / Failed
```

### Common Issues

| Problem | Fix |
|---|---|
| Driver not visible on live map | Check Traccar Client app is running and connected |
| ETA not updating | Vehicle needs GPS coordinates — check Traccar is active |
| Tracking email not received | Check customer contact has a valid email address |
| Driver can't see their trips | Trip must be in Dispatched or In Progress state; driver's Odoo user must be linked to a Driver record |
| Stop has no Navigate button | Customer contact is missing street address or GPS coordinates |
