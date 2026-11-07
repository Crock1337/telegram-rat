import base64

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
