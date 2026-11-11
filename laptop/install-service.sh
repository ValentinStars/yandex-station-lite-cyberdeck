#!/usr/bin/env bash
set -e

SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/station-laptop-server.service"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/server.py"

mkdir -p "$SERVICE_DIR"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Yandex Station Laptop Bridge Daemon
After=graphical-session.target network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $SCRIPT_PATH
Restart=always
RestartSec=3
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_CURRENT_DESKTOP=KDE

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable station-laptop-server.service
systemctl --user restart station-laptop-server.service

echo "[+] Station Laptop Server installed and started via systemd user service!"
echo "[+] Status: $(systemctl --user is-active station-laptop-server.service)"
