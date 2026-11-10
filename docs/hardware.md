# Yandex Station Lite 1 (YNDX-00025, yandexmicro) Hardware Architecture

## 1. Specifications

| Component | Description |
| :--- | :--- |
| **SoC** | Amlogic Meson A113X (AXG) — Quad-core ARM Cortex-A53 @ 1.2 GHz (aarch64) |
| **RAM** | 256 MB DDR3 (238 MB usable Linux RAM) |
| **Storage** | 128 MB SPI NAND Flash (`/dev/ubi0_*` rootfs squashfs ro, `/dev/ubi1_0` bkupgrade/data rw ~87MB) |
| **Audio Amp** | NeoFidelity NTP8910A High Performance 2-CH Digital Audio Amp (I2C `1-002a`) |
| **Capacitive Touch / SAR** | Awinic AW9610X 6-channel SAR controller (I2C `0-0012`, driver `aw9610x_sar`) |
| **LED Controller** | Awinic AW9110 10-channel I2C LED driver (I2C `1-005b`, controlling 3 RGB zones) |
| **Wi-Fi / BT** | Realtek RTL8822CS SDIO Wi-Fi 802.11ac + Bluetooth 5.0 UART |
| **Microphones** | 4x PDM digital MEMS microphones array (ALSA `hw:0,1`, Amlogic PDM controller) |
| **Power** | 5V 2.0A via USB Type-C (DCP / standard 5V, Power Delivery NOT required) |

---

## 2. Pinouts & Testpoints

### 2.1 UART Serial Debug Console
On the bottom PCB side under the silicone base:
* **Baudrate:** `115200 8N1`, Logic level `3.3V`
* **Pads:** `TX`, `RX`, `GND`
* **Kernel Console:** Spawns `/sbin/getty_rabbit_hole`. If unlocked (`androidboot.rh_unlock=1` in cmdline or patched), drops directly into root shell.

### 2.2 Amlogic WorldCup BootROM Recovery (USB Burning Mode)
* Shorting SPI Flash CLK / DAT0 to GND before plugging in Type-C forces the Amlogic A113X BootROM into **WorldCup USB Device Mode** (`ID 1b8e:0xxx`).
* Allows flashing images via `update` / `aml-flash` over standard USB-A to Type-C cable.

### 2.3 I2C Bus Topology
* **`i2c-0` (`0xffd1f000.i2c`):**
  * `0x12` — AW96103 Capacitive Proximity / Touch controller (`aw9610x_sar`)
  * `0x37` — PMIC / Auxiliary regulator
  * `0x50` — I2C EEPROM
* **`i2c-1` (`0xff805000.i2c`):**
  * `0x2a` — NTP8910A Audio Amplifier
  * `0x5b` — AW9110 RGB LED Driver (`micro:red:ringX`, `micro:green:ringX`, `micro:blue:ringX`)

---

## 3. Capacitive Touch & Gesture Matrix (AW9610X)

The top panel uses 3 capacitive zones configured via `aw9610x_sar`:
* **CH0:** Left Zone (Vol - touch pad)
* **CH1:** Center Zone (Alice Action touch pad)
* **CH2:** Right Zone (Vol + touch pad)

Real-time capacitive delta is exported to sysfs:
```bash
cat /sys/devices/platform/soc/ffd00000.cbus/ffd1f000.i2c/i2c-0/0-0012/diff
```
* **Noise floor:** -10 to +40
* **Intentional swipes:** 150 to 4400!
