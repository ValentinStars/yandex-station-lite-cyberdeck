#!/usr/bin/env bash
# OPSEC Terminal Launcher for KDE Plasma / Wayland

export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-KDE}"

TERM_BIN="/usr/bin/kitty"
if ! command -v "$TERM_BIN" >/dev/null 2>&1; then
    TERM_BIN="/usr/bin/konsole"
fi

# 1. cmatrix
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty --title "OPSEC // MATRIX FLOW" sh -c "cmatrix -ab -u 2" &
else
    konsole -p tabtitle="OPSEC Matrix" -e cmatrix -ab -u 2 &
fi
sleep 0.2

# 2. hexdump urandom stream
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty --title "OPSEC // HEXDUMP RANDOM NOISE" sh -c "hexdump -C /dev/urandom" &
else
    konsole -p tabtitle="OPSEC Hexdump" -e sh -c "hexdump -C /dev/urandom" &
fi
sleep 0.2

# 3. opsec
if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
    kitty --title "OPSEC // SECURE RUNTIME" opsec &
else
    konsole -p tabtitle="OPSEC Runtime" -e opsec &
fi
sleep 0.2

# 4. btop
if command -v btop >/dev/null 2>&1; then
    if [ "$TERM_BIN" = "/usr/bin/kitty" ]; then
        kitty --title "OPSEC // SYSTEM SURVEILLANCE" btop &
    else
        konsole -p tabtitle="OPSEC Surveillance" -e btop &
    fi
fi
