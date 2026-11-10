#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import subprocess
import json

PORT = 8888

HTML = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html lang="ru">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>~*~ YANDEX.STATION LITE 2007 CYBER-PANEL ~*~</title>
    <style type="text/css">
        * { box-sizing: border-box; }
        body {
            background-color: #0b1528;
            background-image: 
                radial-gradient(ellipse at top, #1e3c72 0%, #0b1528 70%),
                repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 0, 0, 0.25) 2px, rgba(0, 0, 0, 0.25) 4px);
            color: #ffffff;
            font-family: "Tahoma", "Verdana", "Arial", sans-serif;
            margin: 0;
            padding: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* 2007 WINDOWS VISTA / XP AERO WINDOW */
        .window {
            width: 100%;
            max-width: 490px;
            background: linear-gradient(180deg, #304768 0%, #1c2b42 12%, #131d2e 100%);
            border: 2px solid #5579a8;
            border-top-color: #8bb6eb;
            border-left-color: #8bb6eb;
            border-radius: 8px 8px 4px 4px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.6);
            margin-bottom: 16px;
            overflow: hidden;
        }

        /* VISTA GLASS TITLEBAR */
        .title-bar {
            background: linear-gradient(180deg, 
                rgba(255,255,255,0.7) 0%, 
                rgba(255,255,255,0.2) 49%, 
                rgba(0,0,0,0.1) 50%, 
                rgba(0,0,0,0.4) 100%),
                linear-gradient(90deg, #184e92, #2b74c7, #184e92);
            padding: 5px 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #142a47;
            text-shadow: 1px 1px 2px #000;
            font-size: 13px;
            font-weight: bold;
            color: #ffffff;
            letter-spacing: 0.5px;
        }

        .title-buttons {
            display: flex;
            gap: 3px;
        }

        .win-btn {
            width: 19px;
            height: 17px;
            border-radius: 3px;
            border: 1px solid #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
        }
        .btn-min { background: linear-gradient(180deg, #8dc2ff, #296ec2); color: #fff; }
        .btn-max { background: linear-gradient(180deg, #8dc2ff, #296ec2); color: #fff; }
        .btn-close { background: linear-gradient(180deg, #ff8d8d, #c22929); color: #fff; }

        .window-body {
            padding: 14px;
        }

        /* 2007 MARQUEE TICKER */
        .marquee-box {
            background: #000000;
            border: 2px inset #555;
            color: #39ff14;
            font-family: "Courier New", monospace;
            font-size: 12px;
            padding: 4px;
            margin-bottom: 14px;
            text-shadow: 0 0 6px #39ff14;
        }

        /* WINAMP LCD DISPLAY */
        .winamp-display {
            background: #001205;
            border: 2px inset #005500;
            border-radius: 4px;
            padding: 8px 10px;
            font-family: "Courier New", monospace;
            color: #00ff66;
            text-shadow: 0 0 8px #00ff66;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .winamp-kbps {
            font-size: 11px;
            color: #a3ffb8;
            border-left: 1px solid #005500;
            padding-left: 8px;
            text-align: right;
        }

        /* 2007 WEB 2.0 GLOSSY BUTTONS (AERO / AQUA) */
        .glossy-btn {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 10px 14px;
            font-family: "Tahoma", sans-serif;
            font-size: 13px;
            font-weight: bold;
            color: #ffffff;
            text-shadow: 0 -1px 1px rgba(0,0,0,0.7);
            border: 1px solid #1c3656;
            border-radius: 20px;
            cursor: pointer;
            outline: none;
            overflow: hidden;
            box-shadow: 
                0 3px 6px rgba(0,0,0,0.5), 
                inset 0 1px 0 rgba(255,255,255,0.8),
                inset 0 -1px 2px rgba(0,0,0,0.5);
            transition: all 0.1s ease;
        }

        .glossy-btn::before {
            content: "";
            position: absolute;
            top: 1px;
            left: 5%;
            width: 90%;
            height: 48%;
            background: linear-gradient(180deg, rgba(255,255,255,0.75) 0%, rgba(255,255,255,0.15) 100%);
            border-radius: 18px 18px 14px 14px;
            pointer-events: none;
        }

        .glossy-btn:active {
            transform: translateY(2px);
            box-shadow: 0 1px 2px rgba(0,0,0,0.7), inset 0 2px 4px rgba(0,0,0,0.6);
        }

        /* PALETTES 2007 */
        .btn-orange-glow {
            background: linear-gradient(180deg, #ff9f1a 0%, #eb5d00 50%, #c43e00 100%);
            border-color: #872800;
            font-size: 15px;
            padding: 13px;
        }
        .btn-blue-vista {
            background: linear-gradient(180deg, #4da4ff 0%, #1668c7 50%, #0d468a 100%);
            border-color: #0b3263;
        }
        .btn-green-matrix {
            background: linear-gradient(180deg, #44dd55 0%, #1ea62e 50%, #0f681a 100%);
            border-color: #08400f;
        }
        .btn-red-crimson {
            background: linear-gradient(180deg, #ff4d6d 0%, #c71638 50%, #8a0d24 100%);
            border-color: #630b1b;
        }

        .btn-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 12px;
        }

        /* 2007 FIELDSET & LEGEND */
        fieldset {
            border: 2px groove #5375a3;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 14px;
            background: rgba(10, 20, 35, 0.5);
        }

        legend {
            font-size: 11px;
            font-weight: bold;
            color: #a8d0ff;
            text-transform: uppercase;
            padding: 0 6px;
            text-shadow: 0 0 5px #2b74c7;
        }

        /* 2007 INPUTS & SELECTS */
        .win-input, .win-select {
            width: 100%;
            padding: 7px 9px;
            background: #ffffff;
            color: #000000;
            font-family: "Tahoma", sans-serif;
            font-size: 13px;
            border: 2px inset #7f9db9;
            border-radius: 2px;
            margin-bottom: 8px;
            outline: none;
        }
        .win-input:focus {
            background: #ffffdf;
            border-color: #316ac5;
        }

        /* STATUS BOX IN RETRO TERMINAL */
        .terminal-box {
            background: #000000;
            border: 2px inset #444;
            padding: 8px;
            font-family: "Courier New", monospace;
            font-size: 11px;
            color: #00ff66;
            min-height: 38px;
            line-height: 1.3;
        }

        /* PROGRESS BAR XP / VISTA */
        .vista-progress {
            height: 16px;
            background: #e0e0e0;
            border: 2px inset #999;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 8px;
            position: relative;
        }
        .vista-progress-bar {
            height: 100%;
            width: 0%;
            background: repeating-linear-gradient(
                -45deg,
                #28a745,
                #28a745 10px,
                #48d368 10px,
                #48d368 20px
            );
            box-shadow: inset 0 2px 0 rgba(255,255,255,0.7);
            transition: width 0.05s linear;
        }

        /* 2007 88x31 RETRO BADGES */
        .badges-bar {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 14px;
            flex-wrap: wrap;
        }
        .badge-88 {
            width: 88px;
            height: 31px;
            border: 1px solid #777;
            font-family: "Courier New", monospace;
            font-size: 8px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            line-height: 9px;
            background: #111;
            color: #eee;
            box-shadow: 1px 1px 2px #000;
        }
        .counter-box {
            font-family: "Courier New", monospace;
            font-size: 12px;
            color: #ff334b;
            background: #000;
            border: 1px solid #444;
            padding: 3px 8px;
            margin-top: 10px;
            display: inline-block;
        }
    </style>
</head>
<body>

    <!-- ================== ОКНО 1: ПАНЕЛЬ УПРАВЛЕНИЯ КВАЗАРОМ ================== -->
    <div class="window">
        <div class="title-bar">
            <span>💽 Quasar_Multimedia_Player.exe - [2007 EDITION]</span>
            <div class="title-buttons">
                <div class="win-btn btn-min">_</div>
                <div class="win-btn btn-max">□</div>
                <div class="win-btn btn-close">×</div>
            </div>
        </div>

        <div class="window-body">
            <!-- Бегущая строка -->
            <div class="marquee-box">
                <marquee scrollamount="4">
                    ⚡⚡⚡ ДОБРО ПОЖАЛОВАТЬ В 2007 ГОД! ★ YANDEX STATION LITE AERO CYBER-DECK ★ WINAMP & ICQ 2007 EDITION ★ HARDWARE INPUT INJECTION ACTIVE ⚡⚡⚡
                </marquee>
            </div>

            <!-- Winamp LCD дисплей -->
            <div class="winamp-display">
                <div>
                    <b>[STATUS: ONLINE]</b><br>
                    <span id="winamp-track">ALICE_STATION // WINAMP 5.34</span>
                </div>
                <div class="winamp-kbps">
                    <b>320</b> kbps<br>
                    <b>48</b> kHz
                </div>
            </div>

            <fieldset>
                <legend>Быстрое аппаратное управление (Key 582)</legend>
                <div style="margin-bottom: 10px;">
                    <button class="glossy-btn btn-orange-glow" onclick="callApi('/api/pause')">
                        ❚❚ ПАУЗА / ВОЗОБНОВИТЬ (Key 582)
                    </button>
                </div>
                <div class="btn-grid">
                    <button class="glossy-btn btn-blue-vista" onclick="callApi('/api/voldn')">
                        ◄◄ ГРОМКОСТЬ [-]
                    </button>
                    <button class="glossy-btn btn-blue-vista" onclick="callApi('/api/volup')">
                        ►► ГРОМКОСТЬ [+]
                    </button>
                    <button class="glossy-btn btn-red-crimson" onclick="callApi('/api/mute')">
                        🎙 MUTE МИКРОФОНА
                    </button>
                    <button class="glossy-btn btn-green-matrix" onclick="callApi('/api/stop')">
                        ■ СТОП ПЛЕЕР
                    </button>
                </div>
            </fieldset>

            <fieldset>
                <legend>Тихий консольный ввод в DirectiveSequencer</legend>
                <div style="display:flex; gap: 6px;">
                    <input type="text" id="silent-query" class="win-input" value="пауза" placeholder="Напиши команду Алисе..." style="margin-bottom:0;">
                    <button class="glossy-btn btn-blue-vista" style="width: auto; padding: 7px 15px; border-radius: 4px;" onclick="sendQuery()">
                        OK
                    </button>
                </div>
            </fieldset>

            <div class="terminal-box" id="ctrl-status">
                C:\\QUASAR\\BIN&gt; Утилита готова к выполнению команд._
            </div>
        </div>
    </div>

    <!-- ================== ОКНО 2: АКУСТИЧЕСКИЙ ПИНАТЕЛЬ 16-MFSK ================== -->
    <div class="window">
        <div class="title-bar">
            <span>📡 SoundModem_16MFSK_Transmitter.vbp</span>
            <div class="title-buttons">
                <div class="win-btn btn-min">_</div>
                <div class="win-btn btn-max">□</div>
                <div class="win-btn btn-close">×</div>
            </div>
        </div>

        <div class="window-body">
            <fieldset>
                <legend>Режим передачи аудиосигнала</legend>
                <select id="mode" class="win-select" onchange="toggleMode()">
                    <option value="wifi">Акустический Wi-Fi пейринг (SSID + Пароль)</option>
                    <option value="raw">Сырой текст в 16-MFSK (1140-4740 Гц)</option>
                    <option value="sweep">Тестовый синусоидальный свип 1-5 кГц</option>
                </select>

                <div id="wifi-fields">
                    <label style="font-size:11px; font-weight:bold; color:#a8d0ff;">SSID (Имя Wi-Fi):</label>
                    <input type="text" id="ssid" class="win-input" value="Keenetic-7921">
                    
                    <label style="font-size:11px; font-weight:bold; color:#a8d0ff;">Пароль сети:</label>
                    <input type="text" id="wifi-pass" class="win-input" value="SuperSecret2007">
                </div>

                <div id="raw-fields" style="display:none;">
                    <label style="font-size:11px; font-weight:bold; color:#a8d0ff;">Сообщение для передачи:</label>
                    <input type="text" id="raw-text" class="win-input" value="ВЕРНИТЕ МНЕ МОЙ 2007">
                </div>

                <button class="glossy-btn btn-green-matrix" id="playBtn" style="padding:12px; font-size:14px;" onclick="transmitSound()">
                    🔊 ПИНУТЬ ЗВУК С ТЕЛЕФОНА В МИКРОФОН СТАНЦИИ
                </button>

                <div class="vista-progress">
                    <div class="vista-progress-bar" id="progress"></div>
                </div>
            </fieldset>

            <div class="terminal-box" id="status">
                MODEM: Готов. Поднеси динамик телефона к микрофонам станции._
            </div>

            <!-- Ретро-бейджы 2007 года -->
            <div class="badges-bar">
                <div class="badge-88" style="background:#003366; color:#00ffff;">BEST VIEWED<br>1024x768</div>
                <div class="badge-88" style="background:#cc5500; color:#fff;">FIREFOX 2.0<br>RECOMMENDED</div>
                <div class="badge-88" style="background:#222; color:#39ff14;">WINAMP 5<br>INSIDE</div>
                <div class="badge-88" style="background:#660066; color:#ff99ff;">MADE IN<br>NOTEPAD</div>
            </div>

            <div style="text-align:center;">
                <div class="counter-box">
                    СЧЕТЧИК ПОСЕТИТЕЛЕЙ: [ 0 0 1 3 3 7 ]
                </div>
            </div>
        </div>
    </div>

    <script type="text/javascript">
        async function callApi(endpoint) {
            const el = document.getElementById('ctrl-status');
            el.innerText = `C:\\QUASAR&gt; CALL ${endpoint}...`;
            try {
                const res = await fetch(endpoint);
                const data = await res.json();
                el.innerText = `C:\\QUASAR&gt; SUCCESS [${data.msg || data.status}]`;
                document.getElementById('winamp-track').innerText = data.msg || "COMMAND EXECUTED";
            } catch (e) {
                el.innerText = `C:\\QUASAR&gt; ERROR: ${e}`;
            }
        }

        async function sendQuery() {
            const text = document.getElementById('silent-query').value;
            callApi('/api/query?q=' + encodeURIComponent(text));
        }

        const BASE_FREQ = 1140;
        const STEP_FREQ = 240;
        const SYMBOL_DUR = 0.040;
        let audioCtx = null;

        function getAudioContext() {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            return audioCtx;
        }

        function toggleMode() {
            const mode = document.getElementById('mode').value;
            document.getElementById('wifi-fields').style.display = (mode === 'wifi') ? 'block' : 'none';
            document.getElementById('raw-fields').style.display = (mode === 'raw') ? 'block' : 'none';
        }

        function stringToNibbles(str) {
            const utf8Bytes = new TextEncoder().encode(str);
            const nibbles = [];
            for (let b of utf8Bytes) {
                nibbles.push((b >> 4) & 0x0F);
                nibbles.push(b & 0x0F);
            }
            return nibbles;
        }

        async function transmitSound() {
            const ctx = getAudioContext();
            const mode = document.getElementById('mode').value;
            const statusEl = document.getElementById('status');
            const progressEl = document.getElementById('progress');
            const btn = document.getElementById('playBtn');

            btn.disabled = true;
            progressEl.style.width = '0%';

            if (mode === 'sweep') {
                statusEl.innerText = "MODEM: Передача частотного свипа 1000 -> 5000 Гц...";
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1000, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(5000, ctx.currentTime + 1.2);
                gain.gain.setValueAtTime(0.85, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 1.2);
                setTimeout(() => {
                    btn.disabled = false;
                    progressEl.style.width = '100%';
                    statusEl.innerText = "MODEM: Свип 1-5 кГц завершен._";
                }, 1300);
                return;
            }

            let payloadStr = "";
            if (mode === 'wifi') {
                const ssid = document.getElementById('ssid').value;
                const pass = document.getElementById('wifi-pass').value;
                payloadStr = String.fromCharCode(1) + String.fromCharCode(ssid.length) + ssid + String.fromCharCode(pass.length) + pass;
            } else {
                payloadStr = document.getElementById('raw-text').value;
            }

            const dataNibbles = stringToNibbles(payloadStr);
            const preamble = [15, 0, 15, 0, 15, 0, 15, 0];
            const allNibbles = preamble.concat(dataNibbles);

            statusEl.innerText = `MODEM: Модуляция ${allNibbles.length} тонов 16-MFSK (${(allNibbles.length * SYMBOL_DUR).toFixed(1)} сек)...`;

            const startTime = ctx.currentTime + 0.05;
            let curTime = startTime;

            for (let i = 0; i < allNibbles.length; i++) {
                const nibble = allNibbles[i];
                const freq = BASE_FREQ + (STEP_FREQ * nibble);
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, curTime);
                gain.gain.setValueAtTime(0.001, curTime);
                gain.gain.linearRampToValueAtTime(0.85, curTime + 0.004);
                gain.gain.setValueAtTime(0.85, curTime + SYMBOL_DUR - 0.004);
                gain.gain.linearRampToValueAtTime(0.001, curTime + SYMBOL_DUR);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(curTime);
                osc.stop(curTime + SYMBOL_DUR);
                curTime += SYMBOL_DUR;
            }

            const totalDuration = allNibbles.length * SYMBOL_DUR;
            const stepInterval = 50;
            let elapsed = 0;
            const timer = setInterval(() => {
                elapsed += stepInterval / 1000;
                const pct = Math.min(100, (elapsed / totalDuration) * 100);
                progressEl.style.width = pct + '%';
                if (elapsed >= totalDuration) {
                    clearInterval(timer);
                    btn.disabled = false;
                    progressEl.style.width = '100%';
                    statusEl.innerText = `MODEM: [OK] Передано ${allNibbles.length} тонов._`;
                }
            }, stepInterval);
        }
    </script>
</body>
</html>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        query = urllib.parse.parse_qs(url.query)

        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
            return

        resp_data = {"status": "ok"}
        if path == '/api/pause' or path == '/api/play' or path == '/api/stop':
            subprocess.run(['alice-cmd', 'pause'])
            resp_data["msg"] = "ПАУЗА / ВОЗОБНОВЛЕНИЕ (Key 582)"
        elif path == '/api/volup':
            subprocess.run(['alice-cmd', 'volup'])
            resp_data["msg"] = "ГРОМКОСТЬ УВЕЛИЧЕНА (+)"
        elif path == '/api/voldn':
            subprocess.run(['alice-cmd', 'voldn'])
            resp_data["msg"] = "ГРОМКОСТЬ УМЕНЬШЕНА (-)"
        elif path == '/api/mute':
            subprocess.run(['alice-cmd', 'mute'])
            resp_data["msg"] = "MUTE МИКРОФОНА ПЕРЕКЛЮЧЕН"
        elif path == '/api/query':
            q_text = query.get('q', ['пауза'])[0]
            subprocess.run(['alice-cmd', 'query', q_text])
            resp_data["msg"] = f"ТИХИЙ ЗАПРОС '{q_text}' ВЫПОЛНЕН"
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode('utf-8'))

if __name__ == '__main__':
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('', PORT), Handler) as httpd:
        print(f"Serving 2007 style Cyberdeck on port {PORT}...")
        httpd.serve_forever()
