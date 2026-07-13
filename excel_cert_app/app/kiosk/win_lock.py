"""Windows kiosk lock: low-level keyboard hook + focus watchdog.

Swallows the usual escape combos (Alt+Tab, Alt+Esc, Ctrl+Esc, the Win keys,
Alt+F4, F11). Ctrl+Alt+Del cannot be blocked from user mode; the focus
watchdog re-fronts the exam afterwards and every escape is reported via
``on_escape`` for the audit log.
"""
from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

from .base import KioskLock

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_F4 = 0x73
VK_F11 = 0x7A
VK_LWIN = 0x5B
VK_RWIN = 0x5C

LLKHF_ALTDOWN = 0x20


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class WinKioskLock(KioskLock):
    supported = True

    def __init__(self) -> None:
        super().__init__()
        self._hook = None
        self._thread: threading.Thread | None = None
        self._thread_id = None
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._ctrl_down = False

    # -- hook thread -------------------------------------------------------

    def engage(self) -> None:
        if self.engaged:
            return
        self.engaged = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        HOOKPROC = ctypes.CFUNCTYPE(
            ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )
        self._proc = HOOKPROC(self._callback)  # keep a ref alive
        self._thread_id = self._kernel32.GetCurrentThreadId()
        self._hook = self._user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0
        )
        msg = wintypes.MSG()
        while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

    def _callback(self, nCode, wParam, lParam):
        if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            kb = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
            vk = kb.vkCode
            alt = bool(kb.flags & LLKHF_ALTDOWN)
            ctrl = bool(self._user32.GetAsyncKeyState(0x11) & 0x8000)

            blocked = (
                vk in (VK_LWIN, VK_RWIN)
                or (alt and vk == VK_TAB)
                or (alt and vk == VK_ESCAPE)
                or (alt and vk == VK_F4)
                or (ctrl and vk == VK_ESCAPE)
                or vk == VK_F11
            )
            if blocked:
                if self.on_escape:
                    try:
                        self.on_escape(f"key_blocked vk={vk:#x} alt={alt} ctrl={ctrl}")
                    except Exception:
                        pass
                return 1  # swallow the key
        return self._user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    # -- focus watchdog ----------------------------------------------------

    def enforce(self, allowed_hwnds: list[int]) -> None:
        if not self.engaged or not allowed_hwnds:
            return
        fg = self._user32.GetForegroundWindow()
        if fg and fg not in allowed_hwnds:
            # Try to bring the primary allowed window back to front.
            target = allowed_hwnds[0]
            self._user32.SetForegroundWindow(target)
            if self.on_escape:
                try:
                    self.on_escape(f"focus_escape hwnd={fg}")
                except Exception:
                    pass

    def release(self) -> None:
        if not self.engaged:
            return
        self.engaged = False
        try:
            if self._hook:
                self._user32.UnhookWindowsHookEx(self._hook)
            if self._thread_id:
                # WM_QUIT to unblock GetMessageW.
                self._user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        except Exception:
            pass
        finally:
            self._hook = None
