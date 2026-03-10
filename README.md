# Modbus TCP Server & Client

A professional desktop application for Modbus TCP communication built with PySide6 and pymodbus.

![Python](https://img.shields.io/badge/Python-3.14-blue)
![PySide6](https://img.shields.io/badge/PySide6-GUI-green)
![Modbus](https://img.shields.io/badge/Protocol-Modbus%20TCP-orange)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## Features

- **10 holding registers** (R00–R09) with live monitoring
- **Per-register WARN and CRIT setpoints** — editable live via spinboxes
- **Sparkline charts** per register with threshold lines that move with setpoints
- **Alarm panel** showing OK / HIGH / CRITICAL status for each register
- **Write panel** on the client to send values to individual or all registers
- **Auto-reconnect** on the client when server connection is lost
- **Setpoints saved** to `setpoints.json` and shared between server and client
- **Dark modern UI** built with PySide6

---

## Applications

### Modbus Server
- Start/stop a Modbus TCP server on port 5020
- Control register values via sliders
- Set per-register warning and critical thresholds
- Live sparkline chart for each register
- Alarm panel with summary

### Modbus Client
- Connects to the Modbus Server over TCP
- Live monitoring cards for all 10 registers
- Write single or all registers from the write panel
- Per-register setpoints editable on the client side
- Auto-reconnects if server goes offline

---

## Project Files

| File | Description |
|------|-------------|
| `server.py` | Modbus Server application |
| `client.py` | Modbus Client application |
| `setpoints.py` | Shared alarm setpoint store |
| `app_icons.py` | Runtime icon generator (no .ico file needed) |
| `generate_icons.py` | Generates .ico and .png icon files |
| `build.bat` | One-click build script for both EXEs |
| `server_installer.iss` | Inno Setup script for Server installer |
| `client_installer.iss` | Inno Setup script for Client installer |
| `LICENSE.txt` | Software license |

---

## Requirements

```
Python 3.10+
PySide6
pymodbus
Pillow
pyinstaller (for building EXEs)
```

Install all dependencies:
```bash
py -m pip install pyside6 pymodbus pillow pyinstaller
```

---

## Running from Source

**Start the server:**
```bash
py server.py
```

**Start the client:**
```bash
py client.py
```

---

## Building Windows Installers

**Step 1 — Generate icons:**
```bash
py generate_icons.py
```

**Step 2 — Build EXEs:**
```bash
build.bat
```

**Step 3 — Build installers:**
- Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
- Open `server_installer.iss` → Press Ctrl+F9
- Open `client_installer.iss` → Press Ctrl+F9

Installers will be in `installer_output/`.

---

## Usage

1. Launch **Modbus Server** and click **Start Server**
2. Launch **Modbus Client** — it connects automatically
3. Use sliders on the server to change register values
4. Use the **W** and **C** spinboxes to set per-register alarm thresholds
5. Use the **Write panel** on the client to send values to the server

---

## License

See [LICENSE.txt](LICENSE.txt) for full terms.

---

*Built with PySide6 · pymodbus · PyInstaller · Inno Setup*
