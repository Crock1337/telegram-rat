import base64
import sys

_KEY = 0x5A
CREATE_NO_WINDOW = 0x08000000

def _d(s: str) -> str:
    try:
        return "".join(chr(b ^ _KEY) for b in base64.b64decode(s))
    except Exception:
        return ""

_TOKEN   = "PASTE_HERE"
_ADMIN   = "PASTE_HERE"
_API     = "PASTE_HERE"
_LOGIN   = "PASTE_HERE"
_DISCORD = "PASTE_HERE"

TOKEN = _d(_TOKEN)
_admin_raw = _d(_ADMIN)

if not TOKEN or not _admin_raw or not _admin_raw.isdigit():
    print("[!] Config not set. Run encrypt.py and paste the output into modules/config.py")
    print("[!] Expected encrypted values, not plain token/id")
    sys.exit(1)

ADMIN_ID = int(_admin_raw)
