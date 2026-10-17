"""Local Samsung panel brightness control. Python standard library only."""
from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
import http.client
import ipaddress
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import sys
import threading
import time
from datetime import datetime
from daily_schedule import parse_schedule, ScheduleState

APP_NAME = "Samsung IP Brightness"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SamsungIPBrightness"
IPC_PORT = 47864


def clamp(value: int, maximum: int = 50) -> int:
    return max(0, min(maximum, int(value)))


def validate_ip(value: str) -> str:
    address = ipaddress.ip_address(value.strip())
    if address.version != 4 or address.is_unspecified or address.is_multicast or address.is_loopback:
        raise ValueError("Enter the monitor's IPv4 address, e.g. 192.168.1.100.")
    return str(address)


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data: bytes, decrypt: bool = False) -> bytes:
    """Windows DPAPI: token encryption tied to the signed-in Windows user."""
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    # All seven parameters have pointer-compatible positions in both DPAPI calls.
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


def load_config() -> dict:
    path = DATA_DIR / "config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = DATA_DIR / "config.tmp"
    temporary.write_text(json.dumps(config, indent=2), encoding="utf-8")
    temporary.replace(DATA_DIR / "config.json")


class Monitor:
    def __init__(self, host: str, token: str = "", port: int = 1516):
        self.host = validate_ip(host)
        self.token = token
        self.port = port

    def call(self, method: str, **values) -> dict:
        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if method != "createAccessToken":
            if not self.token:
                raise RuntimeError("Pair the monitor first.")
            request["params"] = {"AccessToken": self.token, **values}
        payload = json.dumps(request).encode("utf-8")
        # The monitor presents a self-signed certificate. Only this local panel
        # connection disables verification; there are no internet requests.
        conn = http.client.HTTPSConnection(
            self.host, self.port, timeout=40 if method == "createAccessToken" else 6,
            context=ssl._create_unverified_context(),
        )
        try:
            # Extra HTTP headers cause failures on some Samsung firmware.
            conn.putrequest("POST", "/", skip_accept_encoding=True)
            for key, value in {"Accept": "application/json", "Content-Type": "application/json",
                               "Content-Length": str(len(payload))}.items():
                conn.putheader(key, value)
            conn.endheaders()
            conn.send(payload)
            response = conn.getresponse()
            if response.status != 200:
                raise RuntimeError(f"Monitor returned HTTP {response.status}.")
            data = json.loads(response.read())
            if "result" not in data:
                error = data.get("error", data)
                code = error.get("code") if isinstance(error, dict) else None
                if code in (-32010, -32700):
                    raise RuntimeError("Authorization rejected. Pair the monitor again.")
                if code in (-32601, -32001):
                    raise RuntimeError("This monitor/firmware does not offer this command in its current mode.")
                if code in (-32002, -32003):
                    raise RuntimeError("The monitor rejected the command in its current picture mode.")
                raise RuntimeError(f"Monitor command failed (code {code}).")
            if not isinstance(data["result"], dict):
                raise RuntimeError("Unexpected monitor response.")
            return data["result"]
        finally:
            conn.close()

    def read(self) -> int:
        return int(self.call("backlightControl")["backlight"])

    def set(self, value: int) -> int:
        self.call("backlightControl", backlight=clamp(value))
        return self.read()


def configured_monitor(config: dict) -> Monitor:
    token = protect(base64.b64decode(config["protected_token"]), decrypt=True).decode()
    return Monitor(config["ip"], token)


def run(background: bool = False, initial_offset: int | None = None) -> None:
    import tkinter as tk
    from tkinter import ttk, messagebox

    command = f"offset {initial_offset}" if initial_offset is not None else "background" if background else "show"
    server = socket.socket()
    # Exclusive bind avoids two Windows instances binding the same local port.
    server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        server.bind(("127.0.0.1", IPC_PORT))
        server.listen(4)
    except OSError:
        server.close()
        try:
            with socket.create_connection(("127.0.0.1", IPC_PORT), timeout=2) as client:
                client.sendall(command.encode())
        except OSError:
            messagebox.showerror(APP_NAME, "Cannot contact the running app. Close other instances and try again.")
        return

    commands, events = queue.Queue(), queue.Queue()
    config_lock = threading.Lock()
    scheduler = ScheduleState()
    try:
        config = load_config()
    except (OSError, ValueError):
        config = {}
    active = [None]
    try:
        if config.get("protected_token"):
            active[0] = configured_monitor(config)
    except Exception:
        pass  # A moved Windows account/config requires pairing again.

    def worker():
        while True:
            mode, argument = commands.get()
            try:
                if mode == "pair":
                    candidate = Monitor(argument)
                    result = candidate.call("createAccessToken")
                    candidate.token = result["AccessToken"]
                    current = candidate.read()  # Require brightness support before saving.
                    settings = {"ip": candidate.host, "protected_token": base64.b64encode(
                        protect(candidate.token.encode())).decode()}
                    with config_lock:
                        config.update(settings)
                        save_config(config)
                    active[0] = candidate
                    events.put(("paired", current))
                else:
                    monitor = active[0]
                    if monitor is None:
                        raise RuntimeError("Enter your monitor IP and click Pair monitor.")
                    if mode == "scheduled":
                        generation, key, target = argument
                        if generation != schedule_generation[0] or not config.get('schedule_enabled'):
                            continue
                        current = monitor.set(target)
                        events.put(("scheduled_ok", (generation, key, current)))
                        continue
                    elif mode == "offset":
                        current = monitor.set(monitor.read() + argument)
                    elif mode == "set":
                        current = monitor.set(argument)
                    else:
                        current = monitor.read()
                    events.put(("value", current))
            except Exception as error:
                # Never display raw server payloads, tokens or stack traces.
                if isinstance(error, (KeyError, ValueError)):
                    message = "Unexpected response or unsupported brightness control."
                elif isinstance(error, OSError):
                    message = "Cannot reach monitor. Check power, IP Remote, IP address and network."
                else:
                    message = str(error) if isinstance(error, RuntimeError) else "Pairing/control failed."
                events.put(("scheduled_error", (argument[0], argument[1], message)) if mode == "scheduled"
                           else ("error", message))

    threading.Thread(target=worker, daemon=True).start()

    def listener():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return  # App shutdown closes the listening socket.
            with conn:
                conn.settimeout(2)
                try:
                    text = conn.recv(100).decode("ascii")
                    if text in ("show", "background"):
                        events.put(("command", text))
                    elif text.startswith("offset "):
                        number = int(text.split()[1])
                        commands.put(("offset", clamp(number + 50, 100) - 50))
                except (OSError, ValueError, UnicodeError):
                    pass

    threading.Thread(target=listener, daemon=True).start()
    hotkey_thread = [0]

    def hotkeys():
        user = ctypes.WinDLL("user32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32")
        hotkey_thread[0] = kernel.GetCurrentThreadId()
        registered = []
        for ident, key in ((11, 0x7A), (12, 0x7B)):
            if user.RegisterHotKey(None, ident, 0x4003, key):
                registered.append(ident)
        events.put(("keys", len(registered)))
        message = wintypes.MSG()
        try:
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == 0x0312:
                    commands.put(("offset", 3 if message.wParam == 12 else -3))
        finally:
            for ident in registered:
                user.UnregisterHotKey(None, ident)

    threading.Thread(target=hotkeys, daemon=True).start()
    app = tk.Tk()
    app.title(APP_NAME)
    app.geometry("560x590")
    app.resizable(False, False)
    frame = ttk.Frame(app, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=APP_NAME, font=("Segoe UI", 15)).pack(anchor="w")
    ttk.Label(frame, text="Local panel brightness over your network · no cloud").pack(anchor="w", pady=(0, 12))
    row = ttk.Frame(frame)
    row.pack(fill="x")
    ip = tk.StringVar(value=config.get("ip", ""))
    ttk.Label(row, text="Monitor IP:").pack(side="left")
    entry = ttk.Entry(row, textvariable=ip, width=22)
    entry.pack(side="left", padx=8)
    status = tk.StringVar(value="Enter monitor IP and pair. Enable IP Remote on the monitor first.")

    def pair():
        try:
            address = validate_ip(ip.get())
        except ValueError:
            status.set("Enter a valid monitor IPv4 address, e.g. 192.168.1.100.")
            return
        pair_button.state(["disabled"])
        status.set("Pairing… select Allow on the monitor (up to 40 seconds).")
        commands.put(("pair", address))

    pair_button = ttk.Button(row, text="Pair monitor", command=pair)
    pair_button.pack(side="right")
    value = tk.DoubleVar(value=0)
    label = ttk.Label(frame, text="— / 50")
    label.pack(anchor="e", pady=(12, 0))
    pending = [None]

    def change(raw):
        target = round(float(raw))
        label.configure(text=f"{target} / 50")
        if pending[0]:
            app.after_cancel(pending[0])
        pending[0] = app.after(350, lambda: commands.put(("set", target)))

    slider = ttk.Scale(frame, from_=0, to=50, variable=value, command=change)
    slider.pack(fill="x", pady=8)
    slider.state(["disabled"])
    ttk.Label(frame, textvariable=status, wraplength=495).pack(anchor="w")
    key_status = tk.StringVar(value="Registering keyboard shortcuts…")
    ttk.Label(frame, textvariable=key_status).pack(anchor="w", pady=10)
    ttk.Label(frame, text="Tray sun: click to open · scroll to dim/brighten · right-click for actions.").pack(anchor="w")
    schedule_box = ttk.LabelFrame(frame, text="Daily schedule · local Windows time", padding=10)
    schedule_box.pack(fill="x", pady=(12, 0))
    schedule_enabled = tk.BooleanVar(value=bool(config.get('schedule_enabled', False)))
    schedule_generation = [0]
    ttk.Checkbutton(schedule_box, text="Enable daily schedule (save to apply)", variable=schedule_enabled).pack(anchor='w')
    ttk.Label(schedule_box, text="One time per line: HH:MM=brightness (0–50)").pack(anchor='w')
    schedule_text = tk.Text(schedule_box, height=4, width=35)
    schedule_text.pack(fill='x', pady=5)
    try:
        entries = config.get('schedule', [])
        initial_text = '\n'.join(f"{item['time']}={item['brightness']}" for item in entries)
        schedule_entries = [parse_schedule(initial_text)] if entries else [[]]
    except (ValueError, KeyError, TypeError):
        schedule_entries = [[]]
        schedule_enabled.set(False)
    schedule_text.insert('1.0', initial_text if schedule_entries[0] else '08:00=30\n20:00=15\n23:00=5')
    schedule_note = tk.StringVar(value='Manual changes remain until the next scheduled time.')

    def save_schedule():
        try:
            entries = parse_schedule(schedule_text.get('1.0', 'end'))
            with config_lock:
                config['schedule'] = entries
                config['schedule_enabled'] = schedule_enabled.get()
                save_config(config)
            schedule_entries[0] = entries
            scheduler.reset()
            schedule_generation[0] += 1
            schedule_note.set('Saved. Current time slot applies now.' if schedule_enabled.get() else 'Schedule disabled.')
        except ValueError as error:
            schedule_note.set(str(error))
        except OSError:
            schedule_note.set('Cannot save settings to the Windows user profile.')

    ttk.Button(schedule_box, text='Save schedule', command=save_schedule).pack(anchor='e')
    ttk.Label(schedule_box, textvariable=schedule_note, wraplength=490).pack(anchor='w', pady=(5, 0))
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=12)
    ttk.Button(buttons, text="Refresh", command=lambda: commands.put(("read", None))).pack(side="left")

    def quit_app():
        if hotkey_thread[0]:
            ctypes.windll.user32.PostThreadMessageW(hotkey_thread[0], 0x0012, 0, 0)
        tray.stop()
        server.close()
        app.destroy()

    ttk.Button(buttons, text="Quit app", command=quit_app).pack(side="right")
    app.protocol("WM_DELETE_WINDOW", app.withdraw)

    def show():
        app.deiconify()
        app.lift()
        app.attributes("-topmost", True)
        app.after(200, lambda: app.attributes("-topmost", False))
        if active[0]:
            commands.put(("read", None))

    from windows_tray import TrayIcon
    tray = TrayIcon(lambda kind, payload: events.put((kind, payload)))

    def schedule_tick():
        if config.get('schedule_enabled') and active[0] and schedule_entries[0]:
            due = scheduler.due(schedule_entries[0], datetime.now(), time.monotonic())
            if due:
                key, target = due
                commands.put(('scheduled', (schedule_generation[0], key, target)))
        tray.update(f'{APP_NAME} · {round(value.get())}/50' +
                    (' · Schedule on' if config.get('schedule_enabled') else ''),
                    bool(config.get('schedule_enabled')))
        app.after(1000, schedule_tick)

    def poll():
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == 'scheduled_ok':
                    generation, key, current = payload
                    if generation == schedule_generation[0]:
                        scheduler.finish(key, True)
                        schedule_note.set(f'Applied scheduled brightness: {current}/50')
                    events.put(('value', current))
                elif kind == 'scheduled_error':
                    generation, key, message = payload
                    if generation == schedule_generation[0]:
                        scheduler.finish(key, False)
                        schedule_note.set(message + ' Retrying in 60 seconds.')
                elif kind == 'tray':
                    if payload == 'show':
                        show()
                    elif payload in ('darker', 'brighter'):
                        commands.put(('offset', -3 if payload == 'darker' else 3))
                    elif payload == 'schedule':
                        schedule_enabled.set(not bool(config.get('schedule_enabled')))
                        save_schedule()
                    elif payload == 'quit':
                        quit_app()
                        return
                elif kind == 'wheel':
                    commands.put(('offset', payload))
                elif kind in ("value", "paired"):
                    value.set(payload)
                    label.configure(text=f"{payload} / 50")
                    slider.state(["!disabled"])
                    status.set("Connected. Brightness read from monitor.")
                    pair_button.state(["!disabled"])
                elif kind == "error":
                    status.set(payload)
                    pair_button.state(["!disabled"])
                    if not app.winfo_viewable():
                        show()
                elif kind == "keys":
                    key_status.set("Ctrl + Alt + F11: darker · F12: brighter" if payload == 2
                                   else "A hotkey is occupied. Quit other brightness apps and restart this app.")
                elif kind == "command" and payload == "show":
                    show()
        except queue.Empty:
            pass
        app.after(100, poll)

    if background and active[0]:
        app.withdraw()
    if active[0]:
        commands.put(("offset", initial_offset) if initial_offset is not None else ("read", None))
    poll()
    schedule_tick()
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--background", action="store_true", help="Start hidden after pairing")
    parser.add_argument("--offset", type=int, help="Adjust brightness by this many panel units")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This application requires Windows.")
    run(args.background, args.offset)


if __name__ == "__main__":
    main()
