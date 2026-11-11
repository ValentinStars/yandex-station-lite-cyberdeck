#!/usr/bin/env bash
# georgy-toggle.sh - Toggle Georgiy mode on Yandex Station Lite

STATION_IP="${STATION_IP:-192.168.1.127}"
STATION_PORT="${STATION_PORT:-2222}"

CMD="${1:-toggle}"

case "$CMD" in
    1|on|start|enable)
        TARGET_CMD="on"
        ;;
    0|off|stop|disable)
        TARGET_CMD="off"
        ;;
    status|check)
        TARGET_CMD="status"
        ;;
    *)
        TARGET_CMD="toggle"
        ;;
esac

# 1. Quick network check
if ! ssh -o ConnectTimeout=2 -o BatchMode=yes -p "$STATION_PORT" root@"$STATION_IP" "true" 2>/dev/null; then
    command -v notify-send >/dev/null 2>&1 && notify-send -u critical -i dialog-error "Георгий" "Колонка не отвечает по сети ($STATION_IP:$STATION_PORT)!"
    echo "[-] Станция недоступна по сети root@$STATION_IP:$STATION_PORT" >&2
    exit 1
fi

# 2. Check if daemon is running, start if needed
IS_RUNNING=$(ssh -o BatchMode=yes -p "$STATION_PORT" root@"$STATION_IP" "pidof station-voice-bridge 2>/dev/null || true")
if [ -z "$IS_RUNNING" ]; then
    echo "[*] Запускаю сервис на станции..."
    ssh -o BatchMode=yes -p "$STATION_PORT" root@"$STATION_IP" "/etc/init.d/S98voice-bridge start >/dev/null 2>&1"
    sleep 0.5
fi

# 3. Send command to FIFO and read back status
ssh -o BatchMode=yes -p "$STATION_PORT" root@"$STATION_IP" "echo '$TARGET_CMD' > /tmp/georgy_cmd && sleep 0.3 && cat /tmp/georgy_status 2>/dev/null || true" > /tmp/georgy_status_resp 2>/dev/null

STATUS=$(cat /tmp/georgy_status_resp 2>/dev/null | tr -d ' \n\r')

if [ "$STATUS" = "1" ]; then
    command -v notify-send >/dev/null 2>&1 && notify-send -u normal -i audio-headset "Георгий" "Режим Георгия ВКЛЮЧЕН!\nКолонка слушает твои команды."
    echo "[+] Режим Георгия ВКЛЮЧЕН (колонка перехватывает фразы)"
elif [ "$STATUS" = "0" ]; then
    command -v notify-send >/dev/null 2>&1 && notify-send -u normal -i dialog-information "Георгий" "Режим Георгия ВЫКЛЮЧЕН.\nВернули Алису."
    echo "[*] Режим Георгия ВЫКЛЮЧЕН (работает обычная Алиса)"
else
    command -v notify-send >/dev/null 2>&1 && notify-send -u normal -i audio-headset "Георгий" "Команда отправлена: $TARGET_CMD"
    echo "[*] Команда отправлена: $TARGET_CMD"
fi
