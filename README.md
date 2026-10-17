# Samsung IP Brightness

Control the **actual panel brightness** of a compatible Samsung smart monitor from Windows over your local network. Includes a slider, system tray icon, daily schedule, global keyboard shortcuts and optional startup at sign-in. No cloud account, DDC/CI, service menu, or third-party Python packages required.

**[Deutsche Anleitung](README.de.md)**

## Compatibility

- Tested on **Samsung Odyssey OLED G9 G95SC** with IP Remote enabled, using `backlightControl` over HTTPS port **1516**.
- Other Samsung Tizen monitors/TVs **may** work if they expose the same command. They have not been verified. Firmware and picture mode can affect availability.
- The UI uses the G95SC's **0–50** panel-brightness scale. It does not use `brightnessControl`, which can mean shadow detail on Samsung devices.
- A successful API response is not proof of a visible change on every model. Confirm the panel actually changes before relying on it.

## Requirements

- Windows 10 or 11.
- **Windows EXE:** no Python installation required. The release build targets x64 Windows.
- **Source version only:** [Python 3.10 or newer](https://www.python.org/downloads/windows/) with **Tcl/Tk** and the Python launcher (`py`). The standard Python installer includes these options.
- PC and monitor on the same trusted local network. HDMI/DisplayPort carries the picture; the monitor also needs its own Wi-Fi/network connection.
- **IP Remote** enabled on the monitor. No administrator rights are required for the app.

## Setup

1. Download **`SamsungIPBrightness-windows-x64.zip`** from [Releases](https://github.com/CottTheWizard/samsung-ip-brightness/releases/latest) and extract it to a permanent folder. Start **`SamsungIPBrightness.exe`**; no Python installation is needed. For source code instead, use **Code → Download ZIP** or clone this repository and install Python as above.
2. On the monitor, enable **Settings → All Settings → Connection → Network → Expert Settings → IP Remote**. Menu labels vary by firmware and region. Enable the option in the normal settings; do not change service-menu settings.
3. Find the monitor's IPv4 address under **Network Status → IP Settings**. A router DHCP reservation is recommended so the address stays the same.
4. Double-click **`SamsungIPBrightness.exe`** (binary package) or **`Start.cmd`** (source version). `Start.cmd` automatically uses the EXE if present. Source users can also run `py -3 samsung_brightness.py` in a terminal.
5. Enter **your own monitor IP address** and click **Pair monitor**. Select **Allow** on the monitor within 40 seconds.
6. Move the slider and confirm a visible brightness change. The app checks that `backlightControl` is available before saving the pairing.

The IP field saves valid addresses automatically after typing, on Enter, and when closing the window—even if pairing fails or the monitor is offline. A saved address is separate from a paired connection: after changing it, click **Pair monitor** to authorize that address. Existing pairing credentials are retained for their original address and are never sent automatically to a newly entered IP.

### Shortcuts and automatic startup

Right-click **`Install.ps1` → Run with PowerShell** to create Desktop and Start Menu shortcuts. It asks whether to enable startup at sign-in. If your script policy blocks it, inspect the script and run this from PowerShell in the extracted project folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
```

Keep the extracted folder in place: the shortcuts point to it. Running the installer again updates the shortcuts. This installs shortcuts only; it does not download dependencies or change monitor settings.

## Daily use

| Action | Control |
| --- | --- |
| Darker | **Ctrl + Alt + F11** |
| Brighter | **Ctrl + Alt + F12** |
| Set a value | Slider, 0–50 |
| Reopen window | Desktop/Start Menu shortcut or `Start.cmd` |
| Hide window, keep hotkeys | Close the window |
| Stop background app | **Quit app** |

### System tray

The sun icon appears in the Windows notification area (possibly under **^**). Click it to open the window. **Hover over the sun and scroll up/down to brighten/dim by 3 panel units per notch.** No click or focused window is required. Open the hidden-icons panel first if the sun is under **^**, or drag it onto the taskbar notification area. Scrolling elsewhere is left untouched. High-resolution partial wheel movements accumulate until one notch is reached.

Right-click for **Open**, **Darker**, **Brighter**, **Daily schedule** on/off and **Quit app**. The tooltip shows the latest known brightness. Closing the window keeps the tray icon, schedule and hotkeys running. The icon is restored if Windows Explorer restarts.

### Daily brightness schedule

In the window, enter one local time and brightness per line, for example:

```text
08:00=30
20:00=15
23:00=5
```

Select **Enable daily schedule**, then **Save schedule**. The example is initially **disabled**; it only becomes active when you save it enabled. Times must be unique and use 24-hour `HH:MM`, values must be 0–50. The schedule repeats every day using your **Windows local time**, including local daylight-saving changes.

The latest due entry applies immediately after saving/enabling, on app startup, and after waking from sleep. Before the first time of the day, the previous day's last entry applies. Manual brightness changes remain until the next scheduled entry. If the monitor is unreachable, the app quietly retries after 60 seconds; it does not wake the monitor. The PC and app must be running. No Windows scheduled tasks are created. This version changes brightness directly at the selected time; it does not fade gradually.

Use the tray menu to pause/resume the saved schedule. Settings are stored with the local pairing configuration, outside the repository.

Each keypress changes the panel brightness by **3 units**. The app must be running for hotkeys to work. Only one instance runs: launching it again brings the existing window forward. Pairing/control requests are serialized in a background worker so the window remains responsive.

Optional command-line arguments:

```powershell
py -3 samsung_brightness.py --background
py -3 samsung_brightness.py --offset 3
py -3 samsung_brightness.py --offset -3
```

## Privacy and connection security

- The repository contains **no preconfigured monitor IP, account credentials or paired tokens**.
- Your IP and a **Windows DPAPI-encrypted** token are stored in `%LOCALAPPDATA%\SamsungIPBrightness\config.json`, outside the source folder. Tokens are tied to your Windows user; a copied config requires pairing again on another account/computer.
- No telemetry, ads, cloud service or external runtime network requests. Only the configured monitor and a loopback listener (`127.0.0.1:47864`) are contacted.
- The loopback listener lets another local launch show the app or adjust brightness. Other programs running on the same PC can also request these actions. It is not exposed to the LAN.
- Samsung's local HTTPS endpoint uses a self-signed certificate, so this connection does not verify the certificate. Use a trusted network; **do not expose monitor ports to the internet**.
- The app does not access the service menu or change OLED protection settings.
- Tray scrolling uses a local Windows low-level mouse hook to detect wheel events over this app's icon. Mouse input is not recorded or transmitted. Other mouse events pass through unchanged.

## Troubleshooting

- **No connection:** check monitor power, its network connection, the IP address and IP Remote. Guest Wi-Fi/client isolation/VLAN rules can block the connection. The app uses TCP **1516**; it does not open Windows firewall ports to the LAN.
- **Pairing times out:** watch for and accept the monitor's on-screen permission request. Try again with the monitor showing the normal PC input.
- **Authorization rejected:** enter the IP and click **Pair monitor** again.
- **Command unsupported/rejected:** your model, firmware or current picture mode may not expose `backlightControl`. The app does not change picture modes automatically. Support for all Tizen displays is not claimed.
- **Numbers change but the screen does not:** this firmware may acknowledge the command without applying it. Compare the monitor's own brightness setting; report the model/firmware in an issue. Never attach `config.json` or tokens.
- **Hotkeys do not work:** quit other brightness apps or tools that use these shortcuts, then restart this app. The window reports hotkey conflicts. Some laptops also require **Fn** to send F11/F12. Elevated applications can interfere with shortcuts from a non-elevated app.
- **Window will not open:** run `py -3 samsung_brightness.py` in a terminal to see the error. If `tkinter` is missing, modify/reinstall Python with Tcl/Tk enabled. If the project folder was moved, run `Install.ps1` again.
- **Old private prototype already running:** quit it before using this public app; both use the same hotkeys. This project uses its own configuration folder and does not import private-prototype settings.

## Uninstall

Click **Quit app**, then run `Uninstall.ps1` to remove this app's shortcuts and startup entry. Delete the extracted source folder. To forget pairing too, delete `%LOCALAPPDATA%\SamsungIPBrightness`. The uninstall script deliberately preserves pairing data unless you remove it yourself.

## Development and tests

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m py_compile samsung_brightness.py
```

### Build a standalone EXE

On x64 Windows with Python installed, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Build.ps1
```

The script installs the pinned PyInstaller build dependency, then creates `dist/SamsungIPBrightness.exe`, the Windows ZIP package (including install/uninstall scripts and guides), and `dist/SHA256SUMS.txt`. Only the build machine needs Python. The one-file app extracts bundled runtime files to a temporary folder while running; first startup may take a few seconds. Release binaries are not code-signed. The GitHub **Windows EXE** workflow also builds downloadable artifacts on version tags or manual dispatch. User configuration is outside the project and is not included in the build.

The tests use mocked network responses; they do not contact a real monitor. Schedule tests cover midnight rollover, exact boundaries, manual overrides, retries and the next day. Windows smoke tests cover startup, DPAPI, single-instance behavior, global hotkeys, tray lifecycle and applying a schedule through the GUI. Actual panel control was verified on a G95SC. Other monitors need hardware testing.

## Protocol references

This app is independently implemented using Python's standard library. The local JSON-RPC pairing/transport and command names are described in the community-maintained [Samsung IP Control protocol reference](https://github.com/TheFab21/ha-samsungtv-smart/blob/master/IP_Control_Protocol_Reference.md). Samsung firmware support is model dependent. This project is not affiliated with Samsung.

## License

[MIT](LICENSE).
