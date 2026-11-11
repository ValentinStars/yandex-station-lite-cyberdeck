#!/usr/bin/env bash
set -e

STATION_IP="${1:-192.168.1.127}"
STATION_PORT="${2:-2222}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Deploying Voice Bridge to Yandex Station Lite ($STATION_IP:$STATION_PORT) ==="

# Check connection
if ! ssh -o ConnectTimeout=3 -p "$STATION_PORT" root@"$STATION_IP" "true" 2>/dev/null; then
    echo "[-] Cannot reach station at root@$STATION_IP:$STATION_PORT. Make sure it is online!"
    exit 1
fi

echo "[+] Stopping running service if any..."
ssh -p "$STATION_PORT" root@"$STATION_IP" "killall -9 station-voice-bridge 2>/dev/null || true; rm -f /data/opt/bin/station-voice-bridge"

echo "[+] Uploading station-voice-bridge binary..."
cat "$REPO_DIR/bin/station-voice-bridge" | ssh -p "$STATION_PORT" root@"$STATION_IP" "cat > /data/opt/bin/station-voice-bridge && chmod +x /data/opt/bin/station-voice-bridge"

echo "[+] Uploading voice-triggers.conf..."
ssh -p "$STATION_PORT" root@"$STATION_IP" "mkdir -p /data/opt/etc"
cat "$REPO_DIR/etc/voice-triggers.conf" | ssh -p "$STATION_PORT" root@"$STATION_IP" "cat > /data/opt/etc/voice-triggers.conf"

echo "[+] Uploading sounds..."
ssh -p "$STATION_PORT" root@"$STATION_IP" "mkdir -p /data/opt/sounds"
for sfile in "$REPO_DIR"/sounds/*.wav; do
    fname=$(basename "$sfile")
    cat "$sfile" | ssh -p "$STATION_PORT" root@"$STATION_IP" "cat > /data/opt/sounds/$fname"
done

echo "[+] Uploading init service..."
ssh -p "$STATION_PORT" root@"$STATION_IP" "mount -o remount,rw /"
cat "$REPO_DIR/services/S98voice-bridge" | ssh -p "$STATION_PORT" root@"$STATION_IP" "cat > /etc/init.d/S98voice-bridge && chmod +x /etc/init.d/S98voice-bridge"
ssh -p "$STATION_PORT" root@"$STATION_IP" "sync && mount -o remount,ro /"

echo "[+] Starting service on station..."
ssh -p "$STATION_PORT" root@"$STATION_IP" "/etc/init.d/S98voice-bridge restart"

echo "[✓] Deployment complete! Voice Bridge is running on the station."
