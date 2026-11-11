# Privacy Lockdown & Anti-Telemetry Guide

This document describes how telemetry, log scraping, and cloud tracking were completely stripped from the Yandex Station Lite 1 (`yandexmicro`) without breaking normal Alice voice operations or Spotify streaming.

---

## 1. What was tracking you?

By default, the Yandex Quasar stack runs two aggressive telemetry daemons:
1. **`maind --fluent-bitd`**:
   - Tails `/data/quasar/daemons_logs/*.log` (including `mediad.log` and `maind.log`).
   - Tails `/var/log/messages` (kernel dmesg and system logs).
   - Batches and uploads every track started, listened seconds, skips, and volume changes to `https://clck.yandex.net/quasar/write/json/batch` every 60 seconds.
2. **`maind --telemetry`**:
   - Gathers AppMetrica session events, device IDs, UUIDs, and network profiles.
   - Uploads to `https://report.appmetrica.yandex.net/report`.

Together, these daemons consumed **~40 MB of precious RAM** (out of 238 MB total) and uploaded detailed logs of your activity.

---

## 2. The Solution

### Step 1: Remove daemons from `/system/vendor/quasar/launch.json`
Edit `/system/vendor/quasar/launch.json` and remove the `telemetry` and `fluent-bitd` task blocks entirely.
Keep only:
* `mediad` (audio player)
* `maind` with `--platformd` (core voice assistant)

### Step 2: Null-route tracking domains in `/etc/hosts`
Add loopback redirections to prevent any socket connections:
```text
127.0.0.1   localhost
127.0.1.1   yandex-station-lite
127.0.0.1   clck.yandex.net
127.0.0.1   report.appmetrica.yandex.net
127.0.0.1   appmetrica.yandex.net
127.0.0.1   metrica.yandex.net
127.0.0.1   mobile.yandex.net
```

### Step 3: Clean up existing log databases
Remove historical cached logs:
```bash
rm -rf /data/quasar/daemons_logs/*
rm -rf /data/quasar/appmetrica/*
rm -f /data/quasar/persistent_clickdaemon.db
```

---

## 3. Results
* **`fluent-bitd` & `telemetry` processes:** Terminated permanently.
* **Network leak:** `0` packets to `clck.yandex.net` and `appmetrica`.
* **RAM freed:** Available RAM increased from **~90 MB** to **128+ MB** (+40 MB headroom).
* **Core functionality:** Alice still responds, media playback still works, Cyberdeck 2007 Winamp runs faster.
