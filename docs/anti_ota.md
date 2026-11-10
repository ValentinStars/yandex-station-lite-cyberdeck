# Yandex Station Lite: Anti-OTA Cementing & Root Guide

## 1. Vulnerability & Root Exploit
* Downgrade from factory firmware (e.g. `0.5.1.9`) to vulnerable official signed firmware `0.369.1.46.4778262442.20261013.297.zip` via local DNS redirection and fake Quasar OTA server (`equasar_server.py`).
* Syncd JSON injection: `adbd.remoteActivation: true` opens root ADB on port 5555 without authentication.

---

## 2. Cementing Against Silent Updates (Anti-OTA)

Executed via `/data/opt/bin/yandex-micro-kit.sh all`:
1. **Public RSA Key Stub:**
   Replace `/system/vendor/quasar/ota_script.pub` with a dummy RSA key. Signature verification for official OTA bundles will fail permanently.
2. **Updater Script Stub:**
   Replace `/system/vendor/quasar/device_ota_update.sh` with `exit 0`.
3. **Strip Updater Daemon from launch.json:**
   Remove `--updatesd` task from `/system/vendor/quasar/launch.json`.
4. **Persistent ADB Markers:**
   Create `/data/quasar/activate_adb_quasmodrom` and `/data/quasar/activate_network_adb` and lock with `chattr +i`.
5. **Persistent Dropbear SSH on Port 2222:**
   Host keys stored in `/data/opt/etc/dropbear/hk_ed25519`, autostarted via `/etc/init.d/S99zdropbear`.
