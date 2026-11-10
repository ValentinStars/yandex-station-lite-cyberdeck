# Protocols & Reverse Engineering

## 1. 16-MFSK Acoustic Wi-Fi Provisioning Protocol

Yandex Stations use an audio data modem (**16-MFSK: Multiple Frequency Shift Keying**) to transmit Wi-Fi credentials and pairing tokens into the speaker's microphone array.

### 1.1 Physical Layer (Modulation)
* **Symbol Duration:** 40 ms (25 symbols/sec = 100 bps).
* **Frequencies:** 16 discrete sine tones from 1140 Hz to 4740 Hz with a step of 240 Hz:

$$f_N = 1140 + (240 \times N) \text{ Hz}, \quad N \in [0..15]$$

| Hex Nibble | Frequency (Hz) | Hex Nibble | Frequency (Hz) |
| :---: | :---: | :---: | :---: |
| `0` | 1140 Hz | `8` | 3060 Hz |
| `1` | 1380 Hz | `9` | 3300 Hz |
| `2` | 1620 Hz | `A` | 3540 Hz |
| `3` | 1860 Hz | `B` | 3780 Hz |
| `4` | 2100 Hz | `C` | 4020 Hz |
| `5` | 2340 Hz | `D` | 4260 Hz |
| `6` | 2580 Hz | `E` | 4500 Hz |
| `7` | 2820 Hz | `F` | 4740 Hz |

### 1.2 Packet Framing
* **Preamble:** 8 alternating sync nibbles `[F, 0, F, 0, F, 0, F, 0]` (320 ms) used by the speaker's FFT to calibrate phase and room acoustic profile.
* **Payload Structure:**
  `[Protocol Ver: 0x01] [SSID Len: 1 byte] [SSID bytes] [Pass Len: 1 byte] [Pass bytes] [Auth Type: 0x02]`

---

## 2. Linux Input Subsystem Injection

Directly injecting events into `/dev/input/event1` (`sar0_pad0`) triggers instant actions across the entire Quasar OS without any sound playback or microphone usage:

| Device Node | Key Code | Linux Constant | Hardware Action |
| :--- | :---: | :--- | :--- |
| `/dev/input/event1` | `582` | `KEY_VOICECOMMAND` | **Play / Pause / Stop / Cancel Alice Speech** |
| `/dev/input/event1` | `115` | `KEY_VOLUMEUP` | **Volume [+]** |
| `/dev/input/event1` | `114` | `KEY_VOLUMEDOWN` | **Volume [-]** |
| `/dev/input/event0` | `113` | `KEY_MUTE` | **Hardware Microphone Mute Toggle** |

---

## 3. Local Glagol WebSocket API (Port 1961)

The speaker runs an encrypted local WebSocket service on `wss://<IP>:1961/`.
* Certificates and RSA private keys are stored in `/data/quasar/devices.json`.
* Directives can be injected via `maind --cli` with `'q' Text Input Query` to talk directly to `DirectiveSequencer` and `FastCommandRequester` silently.
