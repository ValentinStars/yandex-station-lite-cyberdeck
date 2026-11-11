#!/usr/bin/env bash
# OPSEC Terminal Launcher for KDE Plasma / Wayland
# Spawns 4 hacker miniatures placed in the 4 corners of the screen

export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-KDE}"

TERM_BIN="/usr/bin/kitty"
if ! command -v "$TERM_BIN" >/dev/null 2>&1; then
    TERM_BIN="/usr/bin/konsole"
fi

WIN_W=520
WIN_H=320
KITTY_OPTS="-o initial_window_width=$WIN_W -o initial_window_height=$WIN_H -o remember_window_size=no"

# 1. cmatrix (Top-Left)
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty $KITTY_OPTS --title "OPSEC_MATRIX" sh -c "cmatrix -ab -u 2" &
else
    konsole -p tabtitle="OPSEC_MATRIX" --geometry "${WIN_W}x${WIN_H}+15+35" -e cmatrix -ab -u 2 &
fi

# 2. hexdump urandom stream (Top-Right)
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty $KITTY_OPTS --title "OPSEC_HEXDUMP" sh -c "hexdump -C /dev/urandom" &
else
    konsole -p tabtitle="OPSEC_HEXDUMP" --geometry "${WIN_W}x${WIN_H}+830+35" -e sh -c "hexdump -C /dev/urandom" &
fi

# 3. opsec (Bottom-Left)
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty $KITTY_OPTS --title "OPSEC_SECURE" opsec &
else
    konsole -p tabtitle="OPSEC_SECURE" --geometry "${WIN_W}x${WIN_H}+15+410" -e opsec &
fi

# 4. htop system monitor (Bottom-Right)
MON_BIN="/usr/bin/htop"
if ! command -v "$MON_BIN" >/dev/null 2>&1; then
    MON_BIN="top"
fi

if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty $KITTY_OPTS --title "OPSEC_SYSTEM" "$MON_BIN" &
else
    konsole -p tabtitle="OPSEC_SYSTEM" --geometry "${WIN_W}x${WIN_H}+830+410" -e "$MON_BIN" &
fi

# Position windows in KDE Wayland via KWin Scripting
(
SCRIPT="/tmp/opsec_kwin_tile.js"
cat << 'EOF' > "$SCRIPT"
var windows = workspace.windowList();
for (var i = 0; i < windows.length; i++) {
    var w = windows[i];
    if (!w.caption) continue;
    if (w.caption.indexOf("OPSEC_MATRIX") !== -1) {
        w.frameGeometry = { x: 15, y: 35, width: 520, height: 320 };
    } else if (w.caption.indexOf("OPSEC_HEXDUMP") !== -1) {
        w.frameGeometry = { x: 830, y: 35, width: 520, height: 320 };
    } else if (w.caption.indexOf("OPSEC_SECURE") !== -1) {
        w.frameGeometry = { x: 15, y: 410, width: 520, height: 320 };
    } else if (w.caption.indexOf("OPSEC_SYSTEM") !== -1) {
        w.frameGeometry = { x: 830, y: 410, width: 520, height: 320 };
    }
}
EOF

# Poll a few times over 2 seconds to catch windows as they map
for attempt in 1 2 3 4; do
    sleep 0.4
    if command -v qdbus6 >/dev/null 2>&1; then
        qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript "$SCRIPT" "opsec_tile" >/dev/null 2>&1
        qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.start >/dev/null 2>&1
        qdbus6 org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "opsec_tile" >/dev/null 2>&1
    fi
done
rm -f "$SCRIPT"
) &
