#!/usr/bin/env python3
import sys
import time
import subprocess
import os

def say_and_wait(text, timeout=12.0):
    log_path = '/bkupgrade/data/quasar/daemons_logs/maind.log'
    
    try:
        f = open(log_path, 'r', errors='ignore')
        f.seek(0, 2)
    except Exception:
        f = None

    # Send vocalize directive to Quasar
    subprocess.run(['/data/opt/bin/station-voice-bridge', 'say', text], check=True)
    
    # Wait for Alice to start and finish speaking via maind log state machine
    t0 = time.time()
    started = False

    while time.time() - t0 < timeout:
        if f is None:
            try:
                f = open(log_path, 'r', errors='ignore')
            except Exception:
                time.sleep(0.05)
                continue

        line = f.readline()
        if not line:
            # Check if file shrunk (rotated)
            try:
                if os.path.getsize(log_path) < f.tell():
                    f.close()
                    f = open(log_path, 'r', errors='ignore')
            except Exception:
                pass
            time.sleep(0.05)
            continue

        if 'onAliceStateChanged: SPEAKING' in line:
            started = True
        elif started and 'onAliceStateChanged: IDLE' in line:
            if f:
                f.close()
            return True

    if f:
        f.close()
    return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        say_and_wait(sys.argv[1])
