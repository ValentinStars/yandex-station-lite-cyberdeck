#!/usr/bin/env python3
"""
Station Laptop Bridge Server
Listens for command requests from Yandex Station Lite on TCP port 9777.
Executes desktop actions in user session and replies with TTS phrase for Alice.
Supports 'Георгий' temporary assistant mode with custom neural Russian male voice.
"""

import os
import sys
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
    """Synthesizes speech using gTTS + pitch down into deep male voice, streams to station aplay"""
    try:
        from gtts import gTTS
        mp3_path = "/tmp/georgy_temp.mp3"
        wav_path = "/tmp/georgy_temp.wav"
        tts = gTTS(text, lang="ru")
        tts.save(mp3_path)
        subprocess.run([
            "ffmpeg", "-y", "-i", mp3_path,
            "-filter_complex", "asetrate=24000*0.82,atempo=1.22",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", wav_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        with open(wav_path, "rb") as f:
            subprocess.run([
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2",
                "-p", str(STATION_PORT), f"root@{STATION_IP}", "aplay -D default"
            ], stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] speak_georgy error: {e}", file=sys.stderr)

def handle_georgy_phrase(phrase):
    p = phrase.lower()
    print(f"[*] Georgy received: \"{phrase}\"")

    if any(w in p for w in ["пока", "хватит", "отключись", "верни алису", "до свидания"]):
        threading.Thread(target=speak_georgy, args=("Бывай! Возвращаю Алису.",), daemon=True).start()
        return "DEACTIVATE"

    elif "терминал" in p:
        term = "kitty &" if os.path.exists("/usr/bin/kitty") else "konsole &"
        subprocess.Popen(term, shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Терминал запустил, босс.",), daemon=True).start()

    elif ("включи" in p or "вруби" in p) and ("блютуз" in p or "блютус" in p or "bluetooth" in p):
        subprocess.Popen("rfkill unblock bluetooth; bluetoothctl power on", shell=True)
        threading.Thread(target=speak_georgy, args=("Блютуз включен.",), daemon=True).start()

    elif ("выключи" in p or "выруби" in p) and ("блютуз" in p or "блютус" in p or "bluetooth" in p):
        subprocess.Popen("bluetoothctl power off", shell=True)
        threading.Thread(target=speak_georgy, args=("Блютуз выключен.",), daemon=True).start()

    elif "хакинг" in p or "хайкинг" in p or "взлом" in p or "опсек" in p:
        subprocess.Popen("/home/valentin_stars/yandex-station-lite-cyberdeck/laptop/launch-opsec.sh &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Включаю опсек.",), daemon=True).start()

    elif ("выруби" in p or "выключи" in p or "потуши" in p) and ("моник" in p or "экран" in p):
        subprocess.Popen("kscreen-doctor --dpms off", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Монитор погасил.",), daemon=True).start()

    elif ("вруби" in p or "включи" in p) and ("моник" in p or "экран" in p):
        subprocess.Popen("kscreen-doctor --dpms on", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Монитор включил.",), daemon=True).start()

    elif "разблокай" in p or "разблокируй" in p:
        subprocess.Popen("kscreen-doctor --dpms on; loginctl unlock-sessions", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Ноутбук разблокирован.",), daemon=True).start()

    elif "заблокай" in p or "заблокируй" in p:
        subprocess.Popen("loginctl lock-session", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Ноутбук заблокирован.",), daemon=True).start()

    elif "ютуб" in p or "youtube" in p:
        subprocess.Popen("xdg-open 'https://youtube.com' &", shell=True, env=os.environ.copy())
        threading.Thread(target=speak_georgy, args=("Ютубчик открыт.",), daemon=True).start()

    else:
        threading.Thread(target=speak_georgy, args=("Слышу тебя, Георгий на связи. Но такую команду пока не добавили.",), daemon=True).start()

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
            threading.Thread(target=speak_georgy, args=("Здорово! Георгий на связи. Чё сделать?",), daemon=True).start()
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
