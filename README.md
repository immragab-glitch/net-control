<p align="center"><img src="icon.png" width="96" alt="Net Control icon"></p>

<h1 align="center">Net Control</h1>
<p align="center">Per-app internet control for Windows — block, allow, prioritize and cap uploads, with a one-click <b>Game Mode</b>.</p>

> 🇪🇬 الشرح بالعربي: [README_AR.md](README_AR.md)

## Features
- **Live list** of every app that is using the internet, with connection counts and total download/upload speed.
- **Allow / Block** any app (Windows Firewall rules, inbound + outbound).
- **Game Mode** — cuts the internet from every app that isn't on your allowed list, and keeps watching every 3 seconds to block new ones. Shows you the list before blocking anything.
- **High Priority** (DSCP 46 via Windows QoS) for games like Roblox.
- **Upload cap** per app (Windows QoS throttle) — the most effective way to keep ping low.
- **Restore All** — removes every rule the app created (all are prefixed `NetCtrl_`).
- Dark UI, Arabic / English toggle, high-DPI aware.

System processes (`svchost.exe`, anything under `C:\Windows`, …) are protected and never blocked.

## Requirements
- Windows 10 / 11
- Python 3.10+ with Tkinter
- `psutil`

```bash
pip install psutil
```

## Run
```bash
pythonw net_control.py
```
The app asks for Administrator rights (needed for firewall and QoS changes).

Optional: create Start Menu shortcut with the proper taskbar icon:
```bash
powershell -ExecutionPolicy Bypass -File install_shortcut.ps1
```

## Default allowed apps
Chrome, TikTok (Store app), Roblox, and common VPN clients (OpenVPN, WireGuard, Proton VPN, NordVPN, ExpressVPN, Windscribe, Psiphon, Cloudflare WARP, Hotspot Shield). Edit them from the UI with **Allow**, or in `DEFAULT_CONFIG` inside `net_control.py`.

## Notes & limits
- Control is per **process**: YouTube in Chrome means Chrome as a whole.
- Download speed can't be capped without a kernel driver; upload caps and priority are what Windows supports natively.
- DSCP priority only helps if your router honours QoS/DSCP.
- An already-open connection of a newly blocked app may survive until the app is restarted.
