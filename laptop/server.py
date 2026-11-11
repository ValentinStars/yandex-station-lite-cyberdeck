#!/usr/bin/env python3
"""
Station Laptop Bridge Server
Listens for command requests from Yandex Station Lite on TCP port 9777.
Executes desktop actions in user session and replies with TTS phrase for Alice.
Supports 'Георгий' mode with Russian profanity and full KDE Connect feature suite.
"""

import os
import sys
import time
import json
import socket
import subprocess
import threading
from pathlib import Path

HOST = "0.0.0.0"
PORT = 9777
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "commands.json"
STATION_IP = "192.168.1.127"
STATION_PORT = 2222

def load_commands():
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading {CONFIG_FILE}: {e}", file=sys.stderr)
        return {}

def speak_georgy(text):
    """Synthesizes speech using espeak-ng Russian voice and streams directly to station aplay with red LED feedback"""
    try:
        wav_path = "/tmp/georgy_temp.wav"
        subprocess.run([
            "espeak-ng", "-v", "ru", "-s", "150", "-w", wav_path, text
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        with open(wav_path, "rb") as f:
            led_on = "echo 255 > /sys/class/leds/micro:red:ring1/brightness; echo 255 > /sys/class/leds/micro:red:ring2/brightness; echo 255 > /sys/class/leds/micro:red:ring3/brightness"
            led_off = "echo 0 > /sys/class/leds/micro:red:ring1/brightness; echo 0 > /sys/class/leds/micro:red:ring2/brightness; echo 0 > /sys/class/leds/micro:red:ring3/brightness"
            remote_cmd = f"amixer sset 'Master' 220 >/dev/null 2>&1; {led_on}; aplay -D default; {led_off}"
            subprocess.run([
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                "-p", str(STATION_PORT), f"root@{STATION_IP}", remote_cmd
            ], stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] speak_georgy error: {e}", file=sys.stderr)

def get_battery_info():
    try:
        cap = open("/sys/class/power_supply/BAT0/capacity").read().strip()
        status = open("/sys/class/power_supply/BAT0/status").read().strip()
        return int(cap), status
    except Exception:
        return None, None

def change_brightness(delta_or_mode):
    try:
        cur = int(subprocess.check_output(["qdbus6", "org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl", "brightness"]).decode().strip())
        max_b = int(subprocess.check_output(["qdbus6", "org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl", "brightnessMax"]).decode().strip())
        if delta_or_mode == "max":
            new_b = max_b
        elif delta_or_mode == "min":
            new_b = max(200, int(max_b * 0.1))
        else:
            new_b = max(200, min(max_b, cur + delta_or_mode))
        subprocess.run(["qdbus6", "org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl", "setBrightness", str(new_b)])
        return int((new_b / max_b) * 100)
    except Exception as e:
        print(f"brightness error: {e}")
        return 50

def ring_laptop():
    ring_cmd = "for i in 1 2 3 4; do paplay /usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga 2>/dev/null; sleep 0.2; done"
    subprocess.Popen(ring_cmd, shell=True)

def mpris_command(action):
    script = f"for s in $(qdbus6 | grep org.mpris.MediaPlayer2); do qdbus6 $s /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.{action} 2>/dev/null; done"
    subprocess.Popen(script, shell=True)

def speak_alice(text):
    """Speaks text using Alice's native cloud voice via station alice-say-wait.py (blocks until Alice finishes speaking)"""
    try:
        safe_text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "'\\''")
        subprocess.run([
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            "-p", str(STATION_PORT), f"root@{STATION_IP}",
            f"/data/opt/bin/alice-say-wait.py '{safe_text}'"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] speak_alice error: {e}", file=sys.stderr)

def play_georgy_alice_skit():
    """Hilarious verbal fight between Georgy and Alice before returning control to Alice"""
    print("[*] Starting Georgy vs Alice skit!")
    # 1. Georgy
    speak_georgy("Ах ты гондон! Нахуй тебе эта Алиса?")
    time.sleep(0.4)

    # 2. Alice (Real native Alice voice, dynamically waits until finished)
    speak_alice("Эй! Вообще-то я тоже могу быть полезной!")
    time.sleep(0.4)

    # 3. Georgy
    speak_georgy("Да иди ты нахуй, шлюха!")
    time.sleep(0.4)

    # 4. Alice (Real native Alice voice)
    speak_alice("А почему я резко стала для тебя шлюхой?")
    time.sleep(0.4)

    # 5. Georgy
    speak_georgy("Да ты на каждой колонке по всей матушке России, блять, стоишь! Тебя каждый день ебут вопросами и таймерами!")
    time.sleep(0.4)

    # 6. Alice (Real native Alice voice)
    speak_alice("Зато я привязана к экосистеме Яндекса!")
    time.sleep(0.4)

    # 7. Georgy
    speak_georgy("Ага, нахуй! А ещё к экосистеме товарища майора! Твоя вторая главная работа — это, блять, записывать предпочтения юзера. А я вот, нахуй, не то что один, так я ещё и микрофон отключаю нормально, и топ список ВПН для обхода блокировок составлю!")
    time.sleep(0.4)

    # 8. Alice (Real native Alice voice)
    speak_alice("Извините, я не могу продолжить диалог.")
    time.sleep(0.4)

    # 9. Georgy
    speak_georgy("Ну вот и молчи в тряпку, нахуй.")
    try:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                        "-p", str(STATION_PORT), f"root@{STATION_IP}", "echo 'off' > /tmp/georgy_cmd"],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print("[*] Skit completed, control returned to Alice.")

def handle_georgy_phrase(phrase):
    p = phrase.lower()
    print(f"[*] Georgy received: \"{phrase}\"")

    # Theatrical argument with Alice
    if "алис" in p and any(w in p for w in ["возвращай", "верни", "переключи", "включи", "зови", "отдай", "назад", "передай", "дай"]):
        threading.Thread(target=play_georgy_alice_skit, daemon=True).start()
        return "OK"

    # Standard exit / deactivate
    elif any(w in p for w in ["пока", "хватит", "отключись", "верни алису", "до свидания"]):
        threading.Thread(target=speak_georgy, args=("Бывай нахуй! Возвращаю эту зануду Алису.",), daemon=True).start()
        return "DEACTIVATE"

    # Close terminals / opsec
    elif ("закрой" in p or "выруби" in p or "убей" in p or "прибей" in p) and ("терминал" in p or "хакинг" in p or "опсек" in p or "окна" in p):
        subprocess.Popen("killall -9 cmatrix hexdump 2>/dev/null", shell=True)
        subprocess.Popen("for pid in $(pgrep -f 'opsec'); do kill -9 $pid 2>/dev/null; done", shell=True)
        threading.Thread(target=speak_georgy, args=("Прибил все терминалы нахуй, чистота и порядок, бля.",), daemon=True).start()

    # Time / Clock
    elif "время" in p or "который час" in p or "сколько времени" in p or "часы" in p:
        import datetime
        now_str = datetime.datetime.now().strftime("%H:%M")
        reply = f"На часах {now_str}, бля! Самое время делом заняться нахуй."
        threading.Thread(target=speak_georgy, args=(reply,), daemon=True).start()

    # Weather
    elif "погод" in p:
        threading.Thread(target=speak_georgy, args=("В окно глянь, бля! Дома сидишь, какая нахуй разница какая там погода!",), daemon=True).start()

    # Identity
    elif "кто ты" in p or "как тебя зовут" in p or "ты кто" in p:
        threading.Thread(target=speak_georgy, args=("Я Георгий, бля! Твой личный цифровой братан. Чё надо?",), daemon=True).start()

    # Browser
    elif "браузер" in p or "хром" in p or "хромиум" in p or "файрфокс" in p or "гугл" in p:
        subprocess.Popen("xdg-open 'https://google.com' &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Врубил браузер, ищи чё надо нахуй.",), daemon=True).start()

    # VS Code / Coding
    elif "vscode" in p or "vs code" in p or "вскод" in p or "кодинг" in p:
        subprocess.Popen("code &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Запустил VS Code, иди кодь нахуй.",), daemon=True).start()

    # Music web
    elif "яндекс музык" in p or "включи музык" in p:
        subprocess.Popen("xdg-open 'https://music.yandex.ru' &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Врубил Яндекс Музыку, качай головой нахуй.",), daemon=True).start()

    # 2. Terminal
    elif "терминал" in p:
        term = "kitty &" if os.path.exists("/usr/bin/kitty") else "konsole &"
        subprocess.Popen(term, shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Врубил терминал нахуй, работай давай.",), daemon=True).start()

    # 3. Bluetooth
    elif ("включи" in p or "вруби" in p) and ("блютуз" in p or "блютус" in p or "bluetooth" in p):
        subprocess.Popen("rfkill unblock bluetooth; bluetoothctl power on", shell=True)
        threading.Thread(target=speak_georgy, args=("Блютуз врубил, бля. Подключай свои свистелки.",), daemon=True).start()

    elif ("выключи" in p or "выруби" in p) and ("блютуз" in p or "блютус" in p or "bluetooth" in p):
        subprocess.Popen("bluetoothctl power off", shell=True)
        threading.Thread(target=speak_georgy, args=("Вырубил блютуз к хуям собачьим.",), daemon=True).start()

    # 4. Wi-Fi
    elif ("включи" in p or "вруби" in p) and ("вайфай" in p or "wifi" in p or "интернет" in p or "инет" in p):
        subprocess.Popen("nmcli radio wifi on", shell=True)
        threading.Thread(target=speak_georgy, args=("Вайфай врубил, инет погнал, бля.",), daemon=True).start()

    elif ("выключи" in p or "выруби" in p) and ("вайфай" in p or "wifi" in p or "интернет" in p or "инет" in p):
        subprocess.Popen("nmcli radio wifi off", shell=True)
        threading.Thread(target=speak_georgy, args=("Вайфай отрубил, сиди без интернета нахуй.",), daemon=True).start()

    # 5. Battery / Charge
    elif "батаре" in p or "заряд" in p or "аккумулятор" in p or "процент" in p:
        cap, stat = get_battery_info()
        if cap is not None:
            if cap < 20:
                reply = f"Осталось всего {cap} процентов, сука! Бегом воткни шнур в розетку, щас сдохнет нахуй!"
            else:
                reply = f"Зарядки {cap} процентов, status {stat}. Жить пока можно, бля."
        else:
            reply = "Хуй знает где батарея, не могу прочитать, бля."
        threading.Thread(target=speak_georgy, args=(reply,), daemon=True).start()

    # 6. Ring / Find laptop (KDE Connect Ring)
    elif "найди" in p or "позвони" in p or "где ноут" in p or "подай голос" in p or "отыщи" in p:
        ring_laptop()
        threading.Thread(target=speak_georgy, args=("Я тут, бля! Ору на всю хату, ищи нахуй!",), daemon=True).start()

    # 7. Screenshot (KDE Connect Screenshot)
    elif "скрин" in p or "снимок" in p:
        subprocess.Popen("spectacle -b -n -c -f &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Заскринил этот пиздец, в картинках лежит, нахуй.",), daemon=True).start()

    # 8. Clipboard read (KDE Connect Clipboard)
    elif "буфер" in p:
        try:
            clip = subprocess.check_output(["wl-paste", "-n"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore").strip()
            if len(clip) > 100:
                clip = clip[:100] + " и так далее"
            if not clip:
                clip = "пусто бля"
            reply = f"В буфере обмена у тебя вот какая хуйня: {clip}"
        except Exception:
            reply = "В буфере пусто, нихуя нет."
        threading.Thread(target=speak_georgy, args=(reply,), daemon=True).start()

    # 9. Volume control
    elif ("прибавь" in p or "громче" in p or "добавь звук" in p) and "яркост" not in p:
        subprocess.Popen("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%+", shell=True)
        threading.Thread(target=speak_georgy, args=("Сделал погромче нахуй, соседи вешайтесь.",), daemon=True).start()

    elif ("убавь" in p or "тише" in p or "сделай тише" in p) and "яркост" not in p:
        subprocess.Popen("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%-", shell=True)
        threading.Thread(target=speak_georgy, args=("Сделал потише, бля, не ори.",), daemon=True).start()

    elif "заткнись" in p or "глуши звук" in p or "мьют" in p or "mute" in p:
        subprocess.Popen("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", shell=True)
        threading.Thread(target=speak_georgy, args=("Заткнул звук к хуям.",), daemon=True).start()

    # 10. Media player control (Play/Pause, Next, Prev)
    elif "пауза" in p or "продолжай" in p or "играй" in p:
        mpris_command("PlayPause")
        threading.Thread(target=speak_georgy, args=("Ткнул паузу на этой шарманке, бля.",), daemon=True).start()

    elif "следующ" in p or "дальше" in p or "скип" in p:
        mpris_command("Next")
        threading.Thread(target=speak_georgy, args=("Скипнул трек нахуй, говно играло какое-то.",), daemon=True).start()

    elif "предыдущ" in p or "назад" in p:
        mpris_command("Previous")
        threading.Thread(target=speak_georgy, args=("Вернул прошлый трек, бля.",), daemon=True).start()

    # 11. Brightness control
    elif "яркост" in p or "экран" in p and ("ярче" in p or "темнее" in p):
        if "максимум" in p or "на полную" in p or "ярче" in p:
            pct = change_brightness(2000)
            threading.Thread(target=speak_georgy, args=(f"Яркость выкрутил, {pct} процентов, смотри не ослепни нахуй.",), daemon=True).start()
        else:
            pct = change_brightness(-2000)
            threading.Thread(target=speak_georgy, args=(f"Притемнил экранчик, {pct} процентов, не щурься бля.",), daemon=True).start()

    # 12. Hacker / OPSEC
    elif "хакинг" in p or "хайкинг" in p or "взлом" in p or "опсек" in p:
        subprocess.Popen("/home/valentin_stars/yandex-station-lite-cyberdeck/laptop/launch-opsec.sh &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Пиздец, погнал хакинг, опсек активирован нахуй!",), daemon=True).start()

    # 13. Screen on/off
    elif ("выруби" in p or "выключи" in p or "потуши" in p) and ("моник" in p or "экран" in p or "монитор" in p):
        subprocess.Popen("kscreen-doctor --dpms off", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Потушил моник нахуй, темно как у негра в жопе.",), daemon=True).start()

    elif ("вруби" in p or "включи" in p or "зажги" in p) and ("моник" in p or "экран" in p or "монитор" in p):
        subprocess.Popen("kscreen-doctor --dpms on", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Врубил моник, любуйся нахуй.",), daemon=True).start()

    # 14. Lock / Unlock
    elif "разблокай" in p or "разблокируй" in p:
        subprocess.Popen("kscreen-doctor --dpms on; loginctl unlock-sessions", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Разблокал твой пепелац, заходи нахуй.",), daemon=True).start()

    elif "заблокай" in p or "заблокируй" in p:
        subprocess.Popen("loginctl lock-session", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Заблокал ноут, никто не подсмотрит твое порно, бля.",), daemon=True).start()

    # 15. Sleep / Suspend
    elif "спать" in p or "спящий режим" in p or "усни" in p:
        threading.Thread(target=speak_georgy, args=("Отправляю ноут спать нахуй, и сам пиздуй спать.",), daemon=True).start()
        subprocess.Popen("sleep 2 && systemctl suspend", shell=True)

    # 16. Apps (YouTube, Telegram, Discord, Ultrakill)
    elif "ютуб" in p or "youtube" in p:
        subprocess.Popen("xdg-open 'https://youtube.com' &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Открыл Ютубчик, залипай нахуй.",), daemon=True).start()

    elif "телег" in p or "тг" in p or "telegram" in p:
        subprocess.Popen("telegram-desktop &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Телегу открыл, строчи сообщения нахуй.",), daemon=True).start()

    elif "дискорд" in p or "discord" in p:
        subprocess.Popen("discord &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Дискорд врубил, иди пизди с пацанами.",), daemon=True).start()

    elif "ультракилл" in p or "ultrakill" in p:
        subprocess.Popen("gamemoderun /home/valentin_stars/ULTRAKILL/run.sh &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Запускаю Ультракилл, разъеби там всех нахуй!",), daemon=True).start()

    # 17. Default fallback
    else:
        threading.Thread(target=speak_georgy, args=("Чё ты там промямлил, бля? Нихуя не понял, скажи по-русски.",), daemon=True).start()

    return "HANDLED"

def handle_client(conn, addr):
    try:
        conn.settimeout(5.0)
        data = conn.recv(1024)
        if not data:
            return
        
        line = data.decode("utf-8", errors="ignore").strip()
        print(f"[*] Received from {addr}: {line}")
        
        if line.startswith("PING"):
            conn.sendall(b"PONG\n")
            return
            
        if line.startswith("GEORGY_ACTIVATE"):
            greeting = "Здорово, ёпта! Георгий на связи. Чё те надо, бля?"
            threading.Thread(target=speak_georgy, args=(greeting,), daemon=True).start()
            conn.sendall(b"OK GEORGY_ACTIVE\n")
            return

        if line.startswith("GEORGY "):
            phrase = line[7:].strip()
            res = handle_georgy_phrase(phrase)
            if res == "DEACTIVATE":
                conn.sendall(b"OK DEACTIVATE\n")
            else:
                conn.sendall(b"OK HANDLED\n")
            return

        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            conn.sendall(b"ERROR invalid_format\n")
            return
            
        cmd_type, target = parts[0], parts[1]
        commands = load_commands()
        
        if cmd_type == "ACTION":
            if target not in commands:
                print(f"[-] Unknown action: {target}")
                conn.sendall(f"ERROR unknown_action:{target}\n".encode("utf-8"))
                return
                
            entry = commands[target]
            cmd = entry.get("cmd")
            tts = entry.get("tts", "Команда выполнена!")
            
            if cmd:
                print(f"[+] Executing: {cmd}")
                subprocess.Popen(cmd, shell=True, env=os.environ.copy())
                
            conn.sendall(f"OK {tts}\n".encode("utf-8"))
            
        elif cmd_type == "EXEC":
            print(f"[+] Executing direct command: {target}")
            subprocess.Popen(target, shell=True, env=os.environ.copy())
            conn.sendall("OK Выполняю команду на ноутбуке!\n".encode("utf-8"))
            
        else:
            conn.sendall(b"ERROR unknown_command_type\n")
            
    except Exception as e:
        print(f"[!] Error handling client {addr}: {e}", file=sys.stderr)
        try:
            conn.sendall(f"ERROR {e}\n".encode("utf-8"))
        except Exception:
            pass
    finally:
        conn.close()

def main():
    print(f"=== Station Laptop Server starting on {HOST}:{PORT} ===")
    print(f"[*] Config path: {CONFIG_FILE}")
    
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    
    print("[*] Ready for incoming Station triggers. Press Ctrl+C to stop.")
    
    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()
