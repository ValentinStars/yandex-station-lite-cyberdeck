#!/usr/bin/env python3
"""
Station Laptop Bridge Server
Listens for command requests from Yandex Station Lite on TCP port 9777.
Executes desktop actions in user session and replies with TTS phrase for Alice.
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

def load_commands():
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading {CONFIG_FILE}: {e}", file=sys.stderr)
        return {}

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
            # Direct shell command
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
