"""Native Windows notification icon; no third-party dependencies."""
import ctypes as c
from ctypes import wintypes as w
import threading


def accumulate_wheel(delta, remainder=0):
    """One notch is 120 units; preserve high-resolution partial notches."""
    total = delta + remainder
    steps = (1 if total >= 0 else -1) * (abs(total) // 120)
    return steps, total - steps * 120


class TrayIcon:
    CALLBACK = 0x8001
    UPDATE = 0x8002

    def __init__(self, emit):
        self.emit = emit
        self.hwnd = None
        self.text = 'Samsung IP Brightness'
        self.schedule_enabled = False
        self.wheel_remainder = 0
        self.wheel_hook = None
        self.hovering = False
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, text, schedule_enabled):
        if self.text == text[:127] and self.schedule_enabled == schedule_enabled:
            return
        self.text = text[:127]
        self.schedule_enabled = schedule_enabled
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, self.UPDATE, 0, 0)

    def stop(self):
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, 0x10, 0, 0)

    def _run(self):
        self.user = u = c.WinDLL('user32', use_last_error=True)
        # Low-level mouse coordinates are physical pixels. Match that coordinate
        # space for icon hit testing even when Tk runs under another DPI context.
        u.SetThreadDpiAwarenessContext.argtypes = [c.c_void_p]
        u.SetThreadDpiAwarenessContext.restype = c.c_void_p
        u.SetThreadDpiAwarenessContext(c.c_void_p(-4))
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

        class IconIdentifier(c.Structure):
            _fields_ = [('size', w.DWORD), ('hwnd', w.HWND), ('id', w.UINT),
                        ('guid', c.c_ubyte * 16)]

        class MouseData(c.Structure):
            _fields_ = [('point', w.POINT), ('mouse_data', w.DWORD),
                        ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]

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
        shell.Shell_NotifyIconGetRect.argtypes = [c.POINTER(IconIdentifier), c.POINTER(w.RECT)]
        shell.Shell_NotifyIconGetRect.restype = c.c_long
        u.WindowFromPoint.argtypes = [w.POINT]
        u.WindowFromPoint.restype = w.HWND
        u.GetAncestor.argtypes = [w.HWND, w.UINT]
        u.GetAncestor.restype = w.HWND
        u.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
        hook_type = c.WINFUNCTYPE(result_type, c.c_int, w.WPARAM, w.LPARAM)
        u.SetWindowsHookExW.argtypes = [c.c_int, hook_type, w.HINSTANCE, w.DWORD]
        u.SetWindowsHookExW.restype = w.HANDLE
        u.CallNextHookEx.argtypes = [w.HANDLE, c.c_int, w.WPARAM, w.LPARAM]
        u.CallNextHookEx.restype = result_type
        u.UnhookWindowsHookEx.argtypes = [w.HANDLE]
        instance = kernel.GetModuleHandleW(None)
        taskbar_created = u.RegisterWindowMessageW('TaskbarCreated')
        data = NotifyData()

        def add():
            data.tip = self.text
            if not shell.Shell_NotifyIconW(0, c.byref(data)):
                self.emit('error', 'Tray icon unavailable; use the desktop shortcut to reopen.')
            else:
                data.version = 4
                shell.Shell_NotifyIconW(4, c.byref(data))

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
                    event = int(lp) & 0xFFFF
                    if event in (0x0200, 0x0406):
                        self.hovering = True
                    elif event in (0x0202, 0x0203, 0x0400, 0x0401):
                        self.emit('tray', 'show')
                    elif event in (0x0205, 0x007B):
                        menu(hwnd)
                    return 0
                if message == self.UPDATE:
                    data.tip = self.text
                    data.flags = 4 | 0x80  # Only change tooltip, preserve callback registration.
                    shell.Shell_NotifyIconW(1, c.byref(data))
                    data.flags = 7 | 0x80
                    data.version = 4
                    shell.Shell_NotifyIconW(4, c.byref(data))
                    return 0
                if message == taskbar_created:
                    add()
                    return 0
                if message == 0x10:
                    if self.wheel_hook:
                        u.UnhookWindowsHookEx(self.wheel_hook)
                        self.wheel_hook = None
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
        data.flags, data.message, data.icon = 7 | 0x80, self.CALLBACK, icon
        add()
        identifier = IconIdentifier()
        identifier.size, identifier.hwnd, identifier.id = c.sizeof(identifier), self.hwnd, 1

        def over_icon(point):
            rect = w.RECT()
            if shell.Shell_NotifyIconGetRect(c.byref(identifier), c.byref(rect)) != 0:
                return False
            if not (rect.left <= point.x < rect.right and rect.top <= point.y < rect.bottom):
                return False
            # A hidden overflow icon may retain its old rectangle. Check the
            # actual window under the pointer so other apps keep normal scrolling.
            root = u.GetAncestor(u.WindowFromPoint(point), 2)
            name = c.create_unicode_buffer(256)
            u.GetClassNameW(root, name, len(name))
            return name.value in ('Shell_TrayWnd', 'Shell_SecondaryTrayWnd',
                                  'NotifyIconOverflowWindow', 'TopLevelWindowForOverflowXamlIsland',
                                  'XamlExplorerHostIslandWindow')

        self._over_icon = over_icon

        def mouse_proc(code, message, pointer):
            if code >= 0 and message == 0x0200 and self.hovering:
                try:
                    mouse = c.cast(pointer, c.POINTER(MouseData)).contents
                    if not self._over_icon(mouse.point):
                        self.hovering = False
                        self.wheel_remainder = 0
                except Exception:
                    self.hovering = False
            if code >= 0 and message == 0x020A:  # WM_MOUSEWHEEL
                try:
                    mouse = c.cast(pointer, c.POINTER(MouseData)).contents
                    if self.hovering and self._over_icon(mouse.point):
                        delta = c.c_short(mouse.mouse_data >> 16).value
                        steps, self.wheel_remainder = accumulate_wheel(delta, self.wheel_remainder)
                        if steps:
                            self.emit('wheel', steps * 3)
                        return 1  # Consume only wheel events over our own icon.
                    self.wheel_remainder = 0
                except Exception:
                    pass
            return u.CallNextHookEx(self.wheel_hook, code, message, pointer)

        self._mouse_proc = hook_type(mouse_proc)
        self.wheel_hook = u.SetWindowsHookExW(14, self._mouse_proc, instance, 0)
        if not self.wheel_hook:
            self.emit('error', 'Tray wheel unavailable; brightness keys and menu remain available.')
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
