# CamMana Master/Client Sync Testing Guide

## Overview

This guide explains how to test the data synchronization between Master and Client PCs in CamMana.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER PC (Destination)                       │
│                    IP: e.g., 192.168.1.10                        │
├─────────────────────────────────────────────────────────────────┤
│  • Stores all data (history, registered cars, images)            │
│  • Receives sync data from Client nodes                          │
│  • Advertises itself via Zeroconf                                │
│  • sync_config.json: is_destination = true                       │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Network
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT PC (Node)                              │
│                    IP: e.g., 192.168.1.20                        │
├─────────────────────────────────────────────────────────────────┤
│  • Reads data from Master (via proxy)                            │
│  • Sends new check-in/check-out data to Master                   │
│  • Uploads images to Master after processing                     │
│  • sync_config.json: is_destination = false, remote_url set      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Setup Master PC

### 1.1 Configure as Master

On the **Master PC**, make sure `database/sync_config.json` contains:

```json
{
    "remote_url": null,
    "is_destination": true
}
```

### 1.2 Start the Backend

```bash
cd CamMana
uv run python -m backend.server
```

### 1.3 Note the IP Address

Find the Master's IP address:
- Windows: `ipconfig` → Look for IPv4 Address
- The backend will also show it in the Settings page

Example: `http://192.168.1.10:8000`

### 1.4 Check Firewall

Make sure Windows Firewall allows inbound connections on port **8000**.

---

## Step 2: Setup Client PC

### 2.1 Configure as Client

On the **Client PC**, edit `database/sync_config.json`:

```json
{
    "remote_url": "http://192.168.1.10:8000",
    "is_destination": false
}
```

Or use the Login page to configure this automatically.

### 2.2 Start the Backend

```bash
cd CamMana
uv run python -m backend.server
```

---

## Step 3: Run the Test Script

On the **Client PC**, run:

```bash
uv run python tests/test_sync.py
```

### Expected Output (All Tests Pass):

```
============================================================
🔄 CamMana Master/Client Sync Test
============================================================

📋 Current Config:
   is_destination (Master): False
   remote_url: http://192.168.1.10:8000

✅ PASS: Check Client Mode
       Master URL: http://192.168.1.10:8000
✅ PASS: Master Connectivity
       Master PC: MASTER-PC-NAME
✅ PASS: File Sync Endpoint
       Available: True
✅ PASS: Proxy GET History
       Received 15 records
✅ PASS: Proxy GET Registered Cars
       Received 10 cars
✅ PASS: Upload Test Folder
       Uploaded to Master: C:\...\database\car_history\... (2 files)
✅ PASS: Sync Receive Endpoint
       Ping successful

============================================================
📊 Results: 7/7 tests passed
============================================================
```

---

## Step 4: Test Real Check-In/Check-Out

### 4.1 On Client PC

1. Open the frontend: `http://localhost:3000`
2. Go to **Giám sát** (Monitor) page
3. Trigger a manual check-in at a location

### 4.2 Watch the Logs

**Client Backend Logs:**
```
[CheckIn] Syncing folder to Master: C:\...\database\car_history\27-01-2026\uuid_in_11-45-00
[FileSync] Uploaded folder to master: uuid_in_11-45-00 (5 files)
[CheckIn] Folder synced to Master: C:\...\database\car_history\27-01-2026\uuid_in_11-45-00
```

**Master Backend Logs:**
```
[FileSync] Received folder from CLIENT-PC: uuid_in_11-45-00 with 5 files
Updated folder_path for record uuid...
```

### 4.3 Verify on Master

1. Open the Master's frontend: `http://192.168.1.10:3000`
2. Go to **Lịch sử** (History) page
3. You should see the new record from the Client
4. Click on the record to view images (should load correctly)

---

## Step 5: Verify Data on Master

### Check History CSV

On Master PC:
```
database/csv_data/history_27-01-2026.csv
```

Should contain the record from Client with `folder_path` pointing to Master's local path.

### Check Images

On Master PC:
```
database/car_history/27-01-2026/uuid_in_11-45-00/
  ├── Cam1_plate_detect.jpg
  ├── Cam2_wheel_detect.jpg
  ├── checkin_status.json
  └── model_plate.json
```

---

## Troubleshooting

### Test 1 Fails: "Not in client mode"

**Solution:** Edit `database/sync_config.json`:
```json
{
    "remote_url": "http://MASTER_IP:8000",
    "is_destination": false
}
```

### Test 2 Fails: Cannot connect to Master

**Check:**
1. Is Master PC running the backend?
2. Is the IP address correct?
3. Are both PCs on the same network?
4. Is Windows Firewall blocking port 8000?

**Fix Firewall:**
```powershell
# Run as Administrator on Master PC
netsh advfirewall firewall add rule name="CamMana Backend" dir=in action=allow protocol=TCP localport=8000
```

### Test 6 Fails: Upload Failed

**Check:**
1. Is Master running the latest version with `file_sync_router`?
2. Restart Master backend

### No Images on Master

**Check:**
- The record's `folder_path` should point to Master's local path, not Client's path
- If still showing Client's path, the `update_folder_path` sync failed

---

## Quick Reference: Sync Config

| Mode | is_destination | remote_url |
|------|----------------|------------|
| Master | `true` | `null` |
| Client | `false` | `http://MASTER_IP:8000` |

---

## What Gets Synced

| Data Type | Master → Client (Read) | Client → Master (Write) |
|-----------|------------------------|-------------------------|
| Registered Cars | ✅ Proxy GET | ✅ Proxy POST/PUT/DELETE |
| History | ✅ Proxy GET | ✅ Sync Broadcast + File Upload |
| Locations | ✅ Proxy GET | ✅ Proxy POST/PUT/DELETE |
| Camera Types | ✅ Proxy GET | ✅ Proxy POST/PUT/DELETE |
| Cameras | ✅ Proxy GET | ✅ Proxy POST/PUT/DELETE |
| Reports | ✅ Proxy GET | Generated on Master |
| Images | ✅ Served from Master | ✅ Uploaded after check-in/out |
