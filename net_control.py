# -*- coding: utf-8 -*-
"""
متحكم النت - Net Control
يتحكم في وصول كل برنامج للنت على Windows:
  * يمنع/يسمح لأي برنامج عن طريق Windows Firewall
  * وضع اللعب: يقفل النت عن كل البرامج اللي مش في قايمة المسموح تلقائياً
  * أولوية عالية للعبة (DSCP) وتحديد سرعة الرفع للبرامج التانية (Windows QoS)
كل القواعد اللي البرنامج بيعملها اسمها بيبدأ بـ NetCtrl_ وزرار "إرجاع كل حاجة" بيمسحها كلها.
لازم يشتغل كـ Administrator.
"""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, simpledialog, ttk

import psutil

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
PREFIX = "NetCtrl_"
APP_ID = "NetControl.App.1"
CREATE_NO_WINDOW = 0x08000000
WINDOWS_DIR = os.environ.get("SystemRoot", r"C:\Windows").lower()

DEFAULT_CONFIG = {
    # البرامج المسموح لها دايماً (اسم ملف exe بحروف صغيرة)
    "allowed": [
        "chrome.exe",                      # يوتيوب
        "tiktok.exe", "msedgewebview2.exe",  # تطبيق تيك توك
        "robloxplayerbeta.exe", "robloxstudiobeta.exe", "robloxplayerlauncher.exe",
        # برامج VPN مشهورة
        "openvpn.exe", "openvpn-gui.exe", "wireguard.exe", "protonvpn.exe",
        "protonvpn.client.exe", "protonvpnservice.exe", "nordvpn.exe",
        "nordvpn-service.exe", "expressvpn.exe", "expressvpnd.exe",
        "windscribe.exe", "windscribeservice.exe", "psiphon3.exe",
        "hotspotshieldvpn.exe", "warp-svc.exe", "cloudflare warp.exe",
    ],
    "blocked": {},                      # المسار الكامل -> الاسم
    "priority": ["robloxplayerbeta.exe"],
    "upload_limits": {},                # اسم البرنامج -> كيلوبايت/ثانية
    "game_mode": False,
    "lang": "ar",                       # ar / en
}

# برامج مينفعش تتقفل وإلا النت كله هيقع
PROTECTED_NAMES = {
    "system", "system idle process", "svchost.exe", "lsass.exe", "services.exe",
    "wininit.exe", "csrss.exe", "smss.exe", "dns.exe", "spoolsv.exe",
    "python.exe", "pythonw.exe",
}

# ---------------------------------------------------------------- الترجمة
TEXT = {
    "ar": {
        "title": "متحكم النت",
        "subtitle": "اتحكم في النت لكل برنامج على جهازك",
        "upload": "رفع", "download": "تحميل",
        "game_on": "وضع اللعب: شغال", "game_off": "وضع اللعب: مقفول",
        "hint_on": "البرامج اللي مش في قايمة المسموح النت مقفول عنها",
        "hint_off": "شغّله عشان يقفل النت عن أي برنامج مش محتاجه",
        "col_name": "البرنامج", "col_state": "الحالة", "col_conns": "الاتصالات",
        "col_prio": "أولوية / حد الرفع", "col_path": "المسار",
        "st_allowed": "✔  مسموح", "st_blocked": "✖  ممنوع", "st_system": "نظام", "st_normal": "عادي",
        "lg_allowed": "مسموح", "lg_blocked": "ممنوع", "lg_system": "نظام",
        "prio_high": "⚡ عالية", "up_limit": "رفع ≤ {kb} KB/s",
        "btn_allow": "سماح", "btn_block": "منع", "btn_prio": "أولوية عالية",
        "btn_limit": "تحديد الرفع", "btn_clear": "إلغاء الأولوية/الحد",
        "btn_restore": "إرجاع كل حاجة", "btn_lang": "English",
        "ready": "جاهز", "sep": "، ",
        "notice": "تنبيه", "select_first": "اختار برنامج أو أكتر من الجدول الأول.",
        "wait_prev": "استنى العملية اللي قبلها تخلص...", "working": "جاري التنفيذ...",
        "error": "حصل خطأ: {e}",
        "blocked_auto": "وضع اللعب قفل: {names}", "blocked_msg": "اتمنع: {names}",
        "cannot": "مينفعش",
        "protected": "البرامج دي برامج نظام ولو اتقفلت النت كله هيقع:\n{names}",
        "allowed_msg": "اتسمح: {names}",
        "prio_msg": "أولوية عالية لـ: {names}  (بتشتغل لو الراوتر بيدعم QoS/DSCP)",
        "limit_title": "تحديد الرفع",
        "limit_prompt": "أقصى سرعة رفع بالكيلوبايت/ثانية (مثلاً 100):",
        "limit_msg": "اتحدد الرفع بـ {kb} KB/s لـ: {names}",
        "cleared": "اتشالت الأولوية/الحد.",
        "game_title": "وضع اللعب",
        "game_intro": "وضع اللعب هيقفل النت عن أي برنامج مش في قايمة المسموح.",
        "game_victims": "البرامج اللي هتتقفل دلوقتي:",
        "game_allow_tip": "لو فيه برنامج منهم محتاجه، اختاره ودوس \"سماح\" الأول.",
        "game_confirm": "أشغّل وضع اللعب؟",
        "game_started": "وضع اللعب اشتغل: أي برنامج مش في قايمة المسموح هيتقفل عنه النت.",
        "game_stopped": "وضع اللعب اتقفل وكل البرامج رجعلها النت.",
        "restore_title": "إرجاع كل حاجة",
        "restore_confirm": "هيتمسح كل قواعد المنع والأولوية اللي البرنامج عملها، وكل البرامج هيرجعلها النت. متأكد؟",
        "restored": "رجعت كل حاجة زي ما كانت.",
    },
    "en": {
        "title": "Net Control",
        "subtitle": "Control internet access for every app on your PC",
        "upload": "Upload", "download": "Download",
        "game_on": "Game Mode: ON", "game_off": "Game Mode: OFF",
        "hint_on": "Apps that aren't on the allowed list have no internet",
        "hint_off": "Turn it on to cut the internet from apps you don't need",
        "col_name": "App", "col_state": "Status", "col_conns": "Connections",
        "col_prio": "Priority / Upload cap", "col_path": "Path",
        "st_allowed": "✔  Allowed", "st_blocked": "✖  Blocked", "st_system": "System", "st_normal": "Normal",
        "lg_allowed": "Allowed", "lg_blocked": "Blocked", "lg_system": "System",
        "prio_high": "⚡ High", "up_limit": "Upload ≤ {kb} KB/s",
        "btn_allow": "Allow", "btn_block": "Block", "btn_prio": "High Priority",
        "btn_limit": "Limit Upload", "btn_clear": "Clear Priority/Limit",
        "btn_restore": "Restore All", "btn_lang": "عربي",
        "ready": "Ready", "sep": ", ",
        "notice": "Notice", "select_first": "Select one or more apps from the table first.",
        "wait_prev": "Please wait for the previous action to finish...", "working": "Working...",
        "error": "Error: {e}",
        "blocked_auto": "Game Mode blocked: {names}", "blocked_msg": "Blocked: {names}",
        "cannot": "Not allowed",
        "protected": "These are system processes. Blocking them would cut all internet:\n{names}",
        "allowed_msg": "Allowed: {names}",
        "prio_msg": "High priority for: {names}  (works if your router supports QoS/DSCP)",
        "limit_title": "Limit Upload",
        "limit_prompt": "Max upload speed in KB/s (e.g. 100):",
        "limit_msg": "Upload capped at {kb} KB/s for: {names}",
        "cleared": "Priority/limit removed.",
        "game_title": "Game Mode",
        "game_intro": "Game Mode will block the internet for every app that isn't on the allowed list.",
        "game_victims": "Apps that will be blocked now:",
        "game_allow_tip": "If you need one of them, select it and press \"Allow\" first.",
        "game_confirm": "Turn on Game Mode?",
        "game_started": "Game Mode is on: any app not on the allowed list will be blocked.",
        "game_stopped": "Game Mode is off and all apps have internet again.",
        "restore_title": "Restore All",
        "restore_confirm": "This removes every block and priority rule this app created, and gives all apps internet again. Are you sure?",
        "restored": "Everything is back to how it was.",
    },
}

# ---------------------------------------------------------------- الألوان
C = {
    "bg": "#0e1117", "card": "#161b22", "card2": "#1c222b", "border": "#262d38",
    "text": "#e6edf3", "muted": "#8b949e", "dim": "#5a626d", "accent": "#58a6ff",
    "green": "#2ea043", "green_h": "#3fb950",
    "red": "#da3633", "red_h": "#f85149",
    "amber": "#d29922", "amber_h": "#e3b341",
    "blue": "#1f6feb", "blue_h": "#388bfd",
    "violet": "#6d4fd8", "violet_h": "#8263f0",
    "gray": "#30363d", "gray_h": "#3d444d",
    "row_ok": "#12261b", "row_ok_fg": "#7ee2a0",
    "row_bad": "#2d1517", "row_bad_fg": "#ff9b95",
    "select": "#1f3a5f",
}

ICON_FONT = "Segoe MDL2 Assets"
I = {  # أيقونات Segoe MDL2
    "shield": "\uEA18", "game": "\uE7FC", "check": "\uE73E", "block": "\uE711",
    "bolt": "\uE945", "upload": "\uE898", "download": "\uE896", "clear": "\uE7A7",
    "restore": "\uE777", "info": "\uE946", "globe": "\uE774",
}


# ---------------------------------------------------------------- أدوات النظام
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(exe):
        exe = sys.executable
    params = f'"{os.path.abspath(__file__)}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, APP_DIR, 1)


def set_taskbar_relaunch(hwnd):
    """يقول للويندوز يشغّل البرنامج إزاي وبأنهي أيقونة لما يتعمله Pin في التاسك بار
    (من غير كده الـ Pin بيثبّت pythonw.exe بأيقونة Python)"""
    import uuid
    from ctypes import POINTER, WINFUNCTYPE, Structure, byref, c_long, c_ulong, c_ushort, c_void_p

    class PROPERTYKEY(Structure):
        _fields_ = [("fmtid", ctypes.c_byte * 16), ("pid", c_ulong)]

    class PROPVARIANT(Structure):
        _fields_ = [("vt", c_ushort), ("r1", c_ushort), ("r2", c_ushort), ("r3", c_ushort),
                    ("p", c_void_p), ("p2", c_void_p)]

    def guid(s):
        return (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(s).bytes_le)

    fmt = "9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    values = [
        (5, APP_ID),                                                     # AppUserModel.ID
        (2, f'"{pyw}" "{os.path.abspath(__file__)}"'),                  # RelaunchCommand
        (3, os.path.join(APP_DIR, "icon.ico") + ",0"),                   # RelaunchIconResource
        (4, "Net Control"),                                              # RelaunchDisplayNameResource
    ]
    store = c_void_p()
    iid = guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")  # IPropertyStore
    if ctypes.windll.shell32.SHGetPropertyStoreForWindow(hwnd, byref(iid), byref(store)) != 0:
        return False
    vtbl = ctypes.cast(store, POINTER(POINTER(c_void_p)))[0]
    set_value = WINFUNCTYPE(c_long, c_void_p, POINTER(PROPERTYKEY), POINTER(PROPVARIANT))(vtbl[6])
    commit = WINFUNCTYPE(c_long, c_void_p)(vtbl[7])
    release = WINFUNCTYPE(c_ulong, c_void_p)(vtbl[2])
    ok = True
    try:
        for pid, text in values:
            key = PROPERTYKEY(guid(fmt), pid)
            buf = ctypes.create_unicode_buffer(text)
            pv = PROPVARIANT(vt=31, p=ctypes.addressof(buf))  # VT_LPWSTR
            ok = set_value(store, byref(key), byref(pv)) == 0 and ok
        commit(store)
    finally:
        release(store)
    return ok


def run(cmd):
    """يشغل أمر ويرجع (نجح؟، الناتج)"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=CREATE_NO_WINDOW, timeout=60)
        return p.returncode == 0, (p.stdout + p.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def ps(script):
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def safe_name(name):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


# ------------------------------------------------------------- Firewall / QoS
def fw_block(path, name):
    rule = f"{PREFIX}block_{safe_name(name)}"
    run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule}"])
    ok1, out1 = run(["netsh", "advfirewall", "firewall", "add", "rule", f"name={rule}",
                     "dir=out", "action=block", f"program={path}", "enable=yes"])
    ok2, out2 = run(["netsh", "advfirewall", "firewall", "add", "rule", f"name={rule}",
                     "dir=in", "action=block", f"program={path}", "enable=yes"])
    return ok1 and ok2, out1 or out2


def fw_unblock(name):
    rule = f"{PREFIX}block_{safe_name(name)}"
    return run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule}"])


def enable_dscp_registry():
    # الويندوز في الأجهزة المنزلية بيتجاهل DSCP غير لما القيمة دي تتعمل
    ps(r"New-Item -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\QoS' -Force | Out-Null; "
       r"Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\QoS' "
       r"-Name 'Do not use NLA' -Value '1' -Type String")


def qos_priority(exe):
    name = f"{PREFIX}prio_{safe_name(exe)}"
    return ps(f"Remove-NetQosPolicy -Name {ps_quote(name)} -Confirm:$false -ErrorAction SilentlyContinue; "
              f"New-NetQosPolicy -Name {ps_quote(name)} -AppPathNameMatchCondition {ps_quote(exe)} "
              f"-DSCPAction 46 -NetworkProfile All | Out-Null")


def qos_limit(exe, kbps):
    name = f"{PREFIX}limit_{safe_name(exe)}"
    bits = int(kbps) * 1024 * 8
    return ps(f"Remove-NetQosPolicy -Name {ps_quote(name)} -Confirm:$false -ErrorAction SilentlyContinue; "
              f"New-NetQosPolicy -Name {ps_quote(name)} -AppPathNameMatchCondition {ps_quote(exe)} "
              f"-ThrottleRateActionBitsPerSecond {bits} -NetworkProfile All | Out-Null")


def qos_remove(kind, exe):
    name = f"{PREFIX}{kind}_{safe_name(exe)}"
    return ps(f"Remove-NetQosPolicy -Name {ps_quote(name)} -Confirm:$false -ErrorAction SilentlyContinue")


def remove_everything():
    ps(f"Get-NetFirewallRule -DisplayName '{PREFIX}*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule; "
       f"Get-NetQosPolicy -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like '{PREFIX}*' }} | "
       f"Remove-NetQosPolicy -Confirm:$false")


# --------------------------------------------------------------- جمع البيانات
def is_protected(name, path):
    n = name.lower()
    if n in PROTECTED_NAMES:
        return True
    if not path:
        return True  # مش عارفين مساره = غالباً نظام
    return path.lower().startswith(WINDOWS_DIR)


def scan_network_apps():
    """يرجع dict: المسار -> {name, path, conns, pids}"""
    apps = {}
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        conns = []
    for c in conns:
        if not c.raddr or not c.pid:
            continue
        ip = c.raddr.ip
        if ip.startswith("127.") or ip == "::1":
            continue
        try:
            proc = psutil.Process(c.pid)
            name = proc.name()
            path = proc.exe()
        except Exception:
            name, path = f"pid {c.pid}", ""
        key = path or name
        a = apps.setdefault(key, {"name": name, "path": path, "conns": 0, "pids": set()})
        a["conns"] += 1
        a["pids"].add(c.pid)
    return apps


def fmt_speed(bps):
    if bps >= 1024 * 1024:
        return f"{bps / 1024 / 1024:.2f} MB/s"
    return f"{bps / 1024:.0f} KB/s"


# ------------------------------------------------------------- عناصر الواجهة
def rounded_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class RoundButton(tk.Canvas):
    """زرار بحواف دايرية وأيقونة"""

    def __init__(self, parent, text, icon, command, color, hover, s, rtl=True,
                 fg="#ffffff", height=40, font_size=10, bold=True, min_width=0):
        self.s, self.rtl = s, rtl
        self.color, self.hover_color, self.fg = color, hover, fg
        self.command = command
        self.text_font = tkfont.Font(family="Segoe UI", size=font_size,
                                     weight="bold" if bold else "normal")
        self.icon_font = tkfont.Font(family=ICON_FONT, size=font_size + 1)
        self.text, self.icon = text, icon
        h = s(height)
        w = max(s(min_width), self._content_width() + s(32))
        super().__init__(parent, width=w, height=h, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Enter>", lambda e: self._paint(self.hover_color))
        self.bind("<Leave>", lambda e: self._paint(self.color))
        self.bind("<ButtonRelease-1>", lambda e: self.command())
        self._paint(self.color)

    def _content_width(self):
        w = self.text_font.measure(self.text)
        if self.icon:
            w += self.icon_font.measure(self.icon) + self.s(10)
        return w

    def set(self, text=None, color=None, hover=None):
        if text is not None:
            self.text = text
        if color:
            self.color = color
        if hover:
            self.hover_color = hover
        self._paint(self.color)

    def _paint(self, fill):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        rounded_rect(self, 1, 1, w - 1, h - 1, self.s(10), fill=fill, outline="")
        x = (w - self._content_width()) / 2
        tw = self.text_font.measure(self.text)
        iw = self.icon_font.measure(self.icon) if self.icon else 0
        gap = self.s(10) if self.icon else 0
        if self.rtl:   # عربي: الكلام شمال والأيقونة يمين
            text_x, icon_x = x + tw / 2, x + tw + gap + iw / 2
        else:          # English: icon left, text right
            icon_x, text_x = x + iw / 2, x + iw + gap + tw / 2
        self.create_text(text_x, h / 2, text=self.text, fill=self.fg, font=self.text_font)
        if self.icon:
            self.create_text(icon_x, h / 2 + 1, text=self.icon, fill=self.fg, font=self.icon_font)


class StatCard(tk.Canvas):
    """كارت فيه أيقونة وقيمة (سرعة التحميل/الرفع)"""

    def __init__(self, parent, title, icon, color, s, rtl=True):
        w, h = s(190), s(62)
        super().__init__(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0, bd=0)
        rounded_rect(self, 1, 1, w - 1, h - 1, s(12), fill=C["card"], outline=C["border"])
        r = s(18)
        cx = w - s(30) if rtl else s(30)
        tx = w - s(58) if rtl else s(58)
        anchor = "e" if rtl else "w"
        cy = h / 2
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=C["card2"], outline="")
        self.create_text(cx, cy + 1, text=icon, fill=color, font=(ICON_FONT, 14))
        self.create_text(tx, s(19), text=title, anchor=anchor, fill=C["muted"], font=("Segoe UI", 9))
        self.value = self.create_text(tx, s(41), text="--", anchor=anchor,
                                      fill=C["text"], font=("Segoe UI", 13, "bold"))

    def set(self, text):
        self.itemconfig(self.value, text=text)


# ------------------------------------------------------------------- الواجهة
class App:
    def __init__(self, root):
        self.root = root
        self.cfg = self.load_config()
        self.apps = {}
        self.last_io = psutil.net_io_counters()
        self.last_t = time.time()
        self.busy = False
        self.main = None

        scale = root.winfo_fpixels("1i") / 96.0
        self.s = s = lambda v: int(round(v * scale))

        root.configure(bg=C["bg"])
        self.set_icon()
        w, h = s(960), s(640)
        x = max((root.winfo_screenwidth() - w) // 2, 0)
        y = max((root.winfo_screenheight() - h) // 2 - s(30), 0)
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(s(820), s(520))
        root.after(10, self.dark_titlebar)
        self.setup_style()

        self.build_ui()
        self.tick_speed()
        self.refresh()

    # ---------------- لغة
    @property
    def rtl(self):
        return self.cfg.get("lang", "ar") == "ar"

    def t(self, key, **kw):
        txt = TEXT[self.cfg.get("lang", "ar")][key]
        return txt.format(**kw) if kw else txt

    def names(self, apps):
        return self.t("sep").join(a["name"] for a in apps)

    def toggle_lang(self):
        self.cfg["lang"] = "en" if self.rtl else "ar"
        self.save_config()
        status = self.t("ready")
        self.build_ui()
        self.apply_scan(dict(self.apps))
        self.status.config(text=status)

    # ---------------- بناء الواجهة
    def build_ui(self):
        s, rtl = self.s, self.rtl
        R, L = ("right", "left") if rtl else ("left", "right")
        E = "e" if rtl else "w"
        if self.main is not None:
            self.main.destroy()
        self.root.title(self.t("title"))
        self.main = main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill="both", expand=True)

        # ---------- الهيدر
        header = tk.Frame(main, bg=C["bg"])
        header.pack(fill="x", padx=s(18), pady=(s(16), s(8)))
        title_box = tk.Frame(header, bg=C["bg"])
        title_box.pack(side=R)
        tk.Label(title_box, text=I["shield"], font=(ICON_FONT, 26), fg=C["accent"],
                 bg=C["bg"]).pack(side=R, padx=(s(10), 0) if rtl else (0, s(10)))
        tt = tk.Frame(title_box, bg=C["bg"])
        tt.pack(side=R)
        tk.Label(tt, text=self.t("title"), font=("Segoe UI", 18, "bold"), fg=C["text"],
                 bg=C["bg"]).pack(anchor=E)
        tk.Label(tt, text=self.t("subtitle"), font=("Segoe UI", 9),
                 fg=C["muted"], bg=C["bg"]).pack(anchor=E)

        self.up_card = StatCard(header, self.t("upload"), I["upload"], C["amber_h"], s, rtl)
        self.down_card = StatCard(header, self.t("download"), I["download"], C["accent"], s, rtl)
        self.up_card.pack(side=L, padx=(0, s(10)) if rtl else (s(10), 0))
        self.down_card.pack(side=L)

        # ---------- وضع اللعب + زرار اللغة
        game_row = tk.Frame(main, bg=C["bg"])
        game_row.pack(fill="x", padx=s(18), pady=(s(4), s(10)))
        self.game_btn = RoundButton(game_row, "", I["game"], self.toggle_game_mode,
                                    C["gray"], C["gray_h"], s, rtl, height=48, font_size=12,
                                    min_width=280)
        self.game_btn.pack(side=R)
        self.game_hint = tk.Label(game_row, text="", font=("Segoe UI", 9), fg=C["muted"], bg=C["bg"])
        self.game_hint.pack(side=R, padx=s(14))
        RoundButton(game_row, self.t("btn_lang"), I["globe"], self.toggle_lang,
                    C["violet"], C["violet_h"], s, rtl, height=40, min_width=120).pack(side=L)
        self.update_game_btn()

        # ---------- الجدول
        card = tk.Frame(main, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        card.pack(fill="both", expand=True, padx=s(18))
        cols = ("name", "state", "conns", "prio", "path")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", selectmode="extended",
                                 style="Dark.Treeview")
        widths = {"name": 200, "state": 110, "conns": 95, "prio": 170, "path": 300}
        for c in cols:
            self.tree.heading(c, text=self.t("col_" + c))
            self.tree.column(c, width=s(widths[c]), minwidth=s(60), stretch=(c == "path"),
                             anchor="center" if c in ("state", "conns", "prio") else "w")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview,
                           style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, s(2)), pady=s(2))
        self.tree.pack(side="left", fill="both", expand=True, padx=s(2), pady=s(2))
        self.tree.tag_configure("allowed", background=C["row_ok"], foreground=C["row_ok_fg"])
        self.tree.tag_configure("blocked", background=C["row_bad"], foreground=C["row_bad_fg"])
        self.tree.tag_configure("normal", background=C["card"], foreground=C["text"])
        self.tree.tag_configure("system", background=C["card"], foreground=C["dim"])

        # ---------- الأزرار
        bar = tk.Frame(main, bg=C["bg"])
        bar.pack(fill="x", padx=s(18), pady=s(12))
        buttons = [
            ("btn_allow", I["check"], self.allow_selected, C["green"], C["green_h"]),
            ("btn_block", I["block"], self.block_selected, C["red"], C["red_h"]),
            ("btn_prio", I["bolt"], self.priority_selected, C["amber"], C["amber_h"]),
            ("btn_limit", I["upload"], self.limit_selected, C["blue"], C["blue_h"]),
            ("btn_clear", I["clear"], self.clear_qos_selected, C["gray"], C["gray_h"]),
        ]
        for key, icon, cmd, col, hov in buttons:
            RoundButton(bar, self.t(key), icon, cmd, col, hov, s, rtl).pack(
                side=R, padx=(s(8), 0) if rtl else (0, s(8)))
        RoundButton(bar, self.t("btn_restore"), I["restore"], self.restore_all,
                    C["card2"], C["gray"], s, rtl, fg=C["red_h"]).pack(side=L)

        # ---------- شريط الحالة
        sbar = tk.Frame(main, bg=C["card"])
        sbar.pack(fill="x", side="bottom")
        tk.Label(sbar, text=I["info"], font=(ICON_FONT, 10), fg=C["muted"],
                 bg=C["card"]).pack(side=R, padx=(s(6), s(14)) if rtl else (s(14), s(6)), pady=s(6))
        self.status = tk.Label(sbar, text=self.t("ready"), font=("Segoe UI", 9), fg=C["muted"],
                               bg=C["card"], anchor=E)
        self.status.pack(side=R, fill="x", expand=True)
        legend = tk.Frame(sbar, bg=C["card"])
        legend.pack(side=L, padx=s(14))
        for key, col in (("lg_allowed", C["row_ok_fg"]), ("lg_blocked", C["row_bad_fg"]),
                         ("lg_system", C["dim"])):
            tk.Label(legend, text="●", fg=col, bg=C["card"], font=("Segoe UI", 10)).pack(side="left")
            tk.Label(legend, text=self.t(key), fg=C["muted"], bg=C["card"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(s(2), s(10)))

    # ---------------- شكل
    def set_icon(self):
        ico = os.path.join(APP_DIR, "icon.ico")
        png = os.path.join(APP_DIR, "icon.png")
        try:
            self.root.iconbitmap(default=ico)   # أيقونة التاسك بار بكل المقاسات
        except Exception:
            pass
        try:
            self.icon_img = tk.PhotoImage(file=png)
            self.root.iconphoto(True, self.icon_img)
        except Exception:
            pass

    def dark_titlebar(self):
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            try:
                set_taskbar_relaunch(hwnd)
            except Exception:
                pass
            val = ctypes.c_int(1)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                    break
            # الويندوز 10 مش بيرسم الشريط من جديد غير لما الشباك يتغير
            self.root.withdraw()
            self.root.deiconify()
        except Exception:
            pass

    def setup_style(self):
        s = self.s
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("Dark.Treeview", background=C["card"], fieldbackground=C["card"],
                     foreground=C["text"], rowheight=s(32), borderwidth=0,
                     font=("Segoe UI", 10))
        st.layout("Dark.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.map("Dark.Treeview", background=[("selected", C["select"])],
               foreground=[("selected", "#ffffff")])
        st.configure("Dark.Treeview.Heading", background=C["card2"], foreground=C["muted"],
                     font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
                     padding=(s(6), s(8)))
        st.map("Dark.Treeview.Heading", background=[("active", C["border"])])
        st.configure("Dark.Vertical.TScrollbar", background=C["gray"], troughcolor=C["card"],
                     bordercolor=C["card"], arrowcolor=C["muted"], lightcolor=C["gray"],
                     darkcolor=C["gray"], gripcount=0)
        st.map("Dark.Vertical.TScrollbar", background=[("active", C["gray_h"])])

    # ---------------- إعدادات
    def load_config(self):
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
        cfg["allowed"] = [a.lower() for a in cfg["allowed"]]
        if cfg.get("lang") not in TEXT:
            cfg["lang"] = "ar"
        return cfg

    def save_config(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)

    # ---------------- عرض
    def set_status(self, text):
        self.root.after(0, lambda: self.status.config(text=text))

    def tick_speed(self):
        io = psutil.net_io_counters()
        t = time.time()
        dt = max(t - self.last_t, 0.001)
        down = (io.bytes_recv - self.last_io.bytes_recv) / dt
        up = (io.bytes_sent - self.last_io.bytes_sent) / dt
        self.last_io, self.last_t = io, t
        self.down_card.set(fmt_speed(down))
        self.up_card.set(fmt_speed(up))
        self.root.after(1000, self.tick_speed)

    def update_game_btn(self):
        if self.cfg["game_mode"]:
            self.game_btn.set(text=self.t("game_on"), color=C["green"], hover=C["green_h"])
            self.game_hint.config(text=self.t("hint_on"), fg=C["row_ok_fg"])
        else:
            self.game_btn.set(text=self.t("game_off"), color=C["gray"], hover=C["gray_h"])
            self.game_hint.config(text=self.t("hint_off"), fg=C["muted"])

    def refresh(self):
        def work():
            apps = scan_network_apps()
            self.root.after(0, lambda: self.apply_scan(apps))
        threading.Thread(target=work, daemon=True).start()
        self.root.after(3000, self.refresh)

    def state_of(self, name, path):
        n = name.lower()
        if path and path in self.cfg["blocked"]:
            return "blocked"
        if is_protected(name, path):
            return "system"
        if n in self.cfg["allowed"]:
            return "allowed"
        return "normal"

    def apply_scan(self, apps):
        self.apps = apps
        # البرامج الممنوعة بتفضل ظاهرة حتى لو مفيش ليها اتصالات
        for path, name in self.cfg["blocked"].items():
            if path not in apps:
                apps[path] = {"name": name, "path": path, "conns": 0, "pids": set()}

        # وضع اللعب: أي برنامج جديد مش مسموح يتقفل تلقائياً
        if self.cfg["game_mode"] and not self.busy:
            to_block = [a for a in apps.values() if self.state_of(a["name"], a["path"]) == "normal"]
            if to_block:
                self.block_apps(to_block, auto=True)

        selected = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        order = {"allowed": 0, "normal": 1, "blocked": 2, "system": 3}
        for key, a in sorted(apps.items(), key=lambda kv: (order[self.state_of(kv[1]["name"], kv[1]["path"])],
                                                             -kv[1]["conns"])):
            st = self.state_of(a["name"], a["path"])
            n = a["name"].lower()
            extra = []
            if n in self.cfg["priority"]:
                extra.append(self.t("prio_high"))
            if n in self.cfg["upload_limits"]:
                extra.append(self.t("up_limit", kb=self.cfg["upload_limits"][n]))
            self.tree.insert("", "end", iid=key, tags=(st,),
                             values=("  " + a["name"], self.t("st_" + st), a["conns"],
                                     " | ".join(extra), a["path"]))
        for sel in selected:
            if self.tree.exists(sel):
                self.tree.selection_add(sel)

    # ---------------- أوامر
    def selected_apps(self):
        sel = [self.apps[i] for i in self.tree.selection() if i in self.apps]
        if not sel:
            messagebox.showinfo(self.t("notice"), self.t("select_first"))
        return sel

    def in_background(self, fn, done_msg):
        if self.busy:
            self.set_status(self.t("wait_prev"))
            return
        self.busy = True
        self.set_status(self.t("working"))

        def work():
            try:
                fn()
                self.set_status(done_msg)
            except Exception as e:  # noqa: BLE001
                self.set_status(self.t("error", e=e))
            finally:
                self.busy = False
                self.root.after(0, self.save_config)
        threading.Thread(target=work, daemon=True).start()

    def block_apps(self, apps, auto=False):
        apps = [a for a in apps if a["path"] and not is_protected(a["name"], a["path"])]
        if not apps:
            return

        def fn():
            for a in apps:
                ok, _ = fw_block(a["path"], a["name"])
                if ok:
                    self.cfg["blocked"][a["path"]] = a["name"]
        self.in_background(fn, self.t("blocked_auto" if auto else "blocked_msg", names=self.names(apps)))

    def block_selected(self):
        sel = self.selected_apps()
        if not sel:
            return
        prot = [a["name"] for a in sel if is_protected(a["name"], a["path"])]
        if prot:
            messagebox.showwarning(self.t("cannot"), self.t("protected", names="\n".join(prot)))
        for a in sel:
            n = a["name"].lower()
            if n in self.cfg["allowed"]:
                self.cfg["allowed"].remove(n)
        self.block_apps(sel)

    def allow_selected(self):
        sel = self.selected_apps()
        if not sel:
            return

        def fn():
            for a in sel:
                n = a["name"].lower()
                fw_unblock(a["name"])
                self.cfg["blocked"].pop(a["path"], None)
                if n not in self.cfg["allowed"] and not is_protected(a["name"], a["path"]):
                    self.cfg["allowed"].append(n)
        self.in_background(fn, self.t("allowed_msg", names=self.names(sel)))

    def priority_selected(self):
        sel = self.selected_apps()
        if not sel:
            return

        def fn():
            enable_dscp_registry()
            for a in sel:
                n = a["name"].lower()
                qos_priority(n)
                if n not in self.cfg["priority"]:
                    self.cfg["priority"].append(n)
        self.in_background(fn, self.t("prio_msg", names=self.names(sel)))

    def limit_selected(self):
        sel = self.selected_apps()
        if not sel:
            return
        kb = simpledialog.askinteger(self.t("limit_title"), self.t("limit_prompt"),
                                     minvalue=8, maxvalue=1_000_000, parent=self.root)
        if not kb:
            return

        def fn():
            for a in sel:
                n = a["name"].lower()
                qos_limit(n, kb)
                self.cfg["upload_limits"][n] = kb
        self.in_background(fn, self.t("limit_msg", kb=kb, names=self.names(sel)))

    def clear_qos_selected(self):
        sel = self.selected_apps()
        if not sel:
            return

        def fn():
            for a in sel:
                n = a["name"].lower()
                qos_remove("prio", n)
                qos_remove("limit", n)
                if n in self.cfg["priority"]:
                    self.cfg["priority"].remove(n)
                self.cfg["upload_limits"].pop(n, None)
        self.in_background(fn, self.t("cleared"))

    def toggle_game_mode(self):
        if not self.cfg["game_mode"]:
            victims = sorted({a["name"] for a in self.apps.values()
                              if self.state_of(a["name"], a["path"]) == "normal"})
            msg = self.t("game_intro") + "\n\n"
            if victims:
                msg += self.t("game_victims") + "\n" + "\n".join("• " + v for v in victims)
                msg += "\n\n" + self.t("game_allow_tip")
            msg += "\n\n" + self.t("game_confirm")
            if not messagebox.askyesno(self.t("game_title"), msg):
                return
        self.cfg["game_mode"] = not self.cfg["game_mode"]
        self.update_game_btn()
        self.save_config()
        if self.cfg["game_mode"]:
            def fn():
                enable_dscp_registry()
                for n in self.cfg["priority"]:
                    qos_priority(n)
            self.in_background(fn, self.t("game_started"))
        else:
            blocked = list(self.cfg["blocked"].items())

            def fn():
                for _path, name in blocked:
                    fw_unblock(name)
                self.cfg["blocked"].clear()
            self.in_background(fn, self.t("game_stopped"))

    def restore_all(self):
        if not messagebox.askyesno(self.t("restore_title"), self.t("restore_confirm")):
            return

        def fn():
            remove_everything()
            self.cfg["blocked"].clear()
            self.cfg["priority"] = list(DEFAULT_CONFIG["priority"])
            self.cfg["upload_limits"].clear()
            self.cfg["game_mode"] = False
            self.root.after(0, self.update_game_btn)
        self.in_background(fn, self.t("restored"))


def main():
    if sys.platform != "win32":
        print("Windows only.")
        return
    if not is_admin() and "--no-admin" not in sys.argv:
        relaunch_as_admin()
        return
    try:  # التاسك بار يعرض أيقونة البرنامج بدل أيقونة Python
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass
    try:  # خط واضح على الشاشات عالية الدقة
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
