"""Native Windows notification icon; no third-party dependencies."""
import ctypes as c
from ctypes import wintypes as w
import threading


class TrayIcon:
    CALLBACK = 0x8001
    UPDATE = 0x8002

    def __init__(self, emit):
        self.emit = emit
        self.hwnd = None
        self.text = 'Samsung IP Brightness'
        self.schedule_enabled = False
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, text, schedule_enabled):
        self.text = text[:127]
        self.schedule_enabled = schedule_enabled
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, self.UPDATE, 0, 0)

    def stop(self):
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, 0x10, 0, 0)

    def _run(self):
        self.user = u = c.WinDLL('user32', use_last_error=True)
        shell = c.WinDLL('shell32', use_last_error=True)
        kernel = c.WinDLL('kernel32', use_last_error=True)
        result_type = c.c_ssize_t
        proc_type = c.WINFUNCTYPE(result_type, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

        class WindowClass(c.Structure):
            _fields_ = [('style', w.UINT), ('proc', proc_type), ('class_extra', c.c_int),
                        ('window_extra', c.c_int), ('instance', w.HINSTANCE), ('icon', w.HICON),
                        ('cursor', w.HANDLE), ('background', w.HBRUSH),
                        ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]

        class NotifyData(c.Structure):
            _fields_ = [('size', w.DWORD), ('hwnd', w.HWND), ('id', w.UINT),
                        ('flags', w.UINT), ('message', w.UINT), ('icon', w.HICON),
                        ('tip', w.WCHAR * 128), ('state', w.DWORD), ('mask', w.DWORD),
                        ('info', w.WCHAR * 256), ('version', w.UINT),
                        ('title', w.WCHAR * 64), ('info_flags', w.DWORD),
                        ('guid', c.c_ubyte * 16), ('balloon_icon', w.HICON)]

        kernel.GetModuleHandleW.argtypes = [w.LPCWSTR]
        kernel.GetModuleHandleW.restype = w.HMODULE
        u.RegisterClassW.argtypes = [c.POINTER(WindowClass)]
        u.RegisterClassW.restype = w.ATOM
        u.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                                     c.c_int, c.c_int, c.c_int, c.c_int, w.HWND,
                                     w.HMENU, w.HINSTANCE, c.c_void_p]
        u.CreateWindowExW.restype = w.HWND
        u.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        u.DefWindowProcW.restype = result_type
        u.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        u.DestroyWindow.argtypes = [w.HWND]
        u.CreatePopupMenu.restype = w.HMENU
        u.AppendMenuW.argtypes = [w.HMENU, w.UINT, c.c_size_t, w.LPCWSTR]
        u.TrackPopupMenu.argtypes = [w.HMENU, w.UINT, c.c_int, c.c_int, c.c_int, w.HWND, c.c_void_p]
        u.TrackPopupMenu.restype = w.UINT
        u.DestroyMenu.argtypes = [w.HMENU]
        u.SetForegroundWindow.argtypes = [w.HWND]
        u.CreateIcon.argtypes = [w.HINSTANCE, c.c_int, c.c_int, c.c_ubyte,
                                c.c_ubyte, c.c_void_p, c.c_void_p]
        u.CreateIcon.restype = w.HICON
        u.DestroyIcon.argtypes = [w.HICON]
        u.RegisterWindowMessageW.argtypes = [w.LPCWSTR]
        u.RegisterWindowMessageW.restype = w.UINT
        shell.Shell_NotifyIconW.argtypes = [w.DWORD, c.POINTER(NotifyData)]
        shell.Shell_NotifyIconW.restype = w.BOOL
        instance = kernel.GetModuleHandleW(None)
        taskbar_created = u.RegisterWindowMessageW('TaskbarCreated')
        data = NotifyData()

        def add():
            data.tip = self.text
            if not shell.Shell_NotifyIconW(0, c.byref(data)):
                self.emit('error', 'Tray icon unavailable; use the desktop shortcut to reopen.')

        actions = {1: 'show', 2: 'darker', 3: 'brighter', 4: 'schedule', 5: 'quit'}

        def menu(hwnd):
            handle = u.CreatePopupMenu()
            try:
                for ident, title in ((1, 'Open brightness control'), (2, 'Darker  (-3)'),
                                     (3, 'Brighter  (+3)'), (4, 'Daily schedule'), (5, 'Quit app')):
                    u.AppendMenuW(handle, 8 if ident == 4 and self.schedule_enabled else 0, ident, title)
                point = w.POINT()
                u.GetCursorPos(c.byref(point))
                u.SetForegroundWindow(hwnd)
                selected = u.TrackPopupMenu(handle, 0x0102, point.x, point.y, 0, hwnd, None)
                u.PostMessageW(hwnd, 0, 0, 0)
                if selected in actions:
                    self.emit('tray', actions[selected])
            finally:
                u.DestroyMenu(handle)

        def window_proc(hwnd, message, wp, lp):
            try:
                if message == self.CALLBACK:
                    if lp in (0x0202, 0x0203):
                        self.emit('tray', 'show')
                    elif lp == 0x0205:
                        menu(hwnd)
                    return 0
                if message == self.UPDATE:
                    data.tip = self.text
                    shell.Shell_NotifyIconW(1, c.byref(data))
                    return 0
                if message == taskbar_created:
                    add()
                    return 0
                if message == 0x10:
                    shell.Shell_NotifyIconW(2, c.byref(data))
                    u.DestroyWindow(hwnd)
                    return 0
                if message == 2:
                    u.PostQuitMessage(0)
                    return 0
            except Exception:
                self.emit('error', 'Tray operation failed. Use the desktop shortcut.')
            return u.DefWindowProcW(hwnd, message, wp, lp)

        self._proc = proc_type(window_proc)
        cls = WindowClass()
        cls.proc, cls.instance, cls.name = self._proc, instance, 'SamsungIPBrightnessTray'
        atom = u.RegisterClassW(c.byref(cls))
        if not atom:
            self.emit('error', 'Cannot create tray window.')
            self.ready.set()
            return
        self.hwnd = u.CreateWindowExW(0, cls.name, cls.name, 0, 0, 0, 0, 0, None, None, instance, None)
        if not self.hwnd:
            self.emit('error', 'Cannot create tray window.')
            self.ready.set()
            return
        # Monochrome sun icon, drawn as two 32x32 bit masks.
        mask = bytearray([255] * 128)
        image = bytearray(128)
        for y in range(32):
            for x in range(32):
                dx, dy = x - 15.5, y - 15.5
                radius = dx * dx + dy * dy
                if 30 <= radius <= 65 or (85 <= radius <= 150 and
                    (abs(dx) < 1.5 or abs(dy) < 1.5 or abs(abs(dx) - abs(dy)) < 1.5)):
                    bit = 128 >> (x % 8)
                    index = y * 4 + x // 8
                    mask[index] &= ~bit
                    image[index] |= bit
        icon = u.CreateIcon(instance, 32, 32, 1, 1, bytes(mask), bytes(image))
        data.size, data.hwnd, data.id = c.sizeof(data), self.hwnd, 1
        data.flags, data.message, data.icon = 7, self.CALLBACK, icon
        add()
        self.ready.set()
        message = w.MSG()
        while u.GetMessageW(c.byref(message), None, 0, 0) > 0:
            u.TranslateMessage(c.byref(message))
            u.DispatchMessageW.argtypes = [c.POINTER(w.MSG)]
            u.DispatchMessageW.restype = result_type
            u.DispatchMessageW(c.byref(message))
        self.hwnd = None
        if icon:
            u.DestroyIcon(icon)
