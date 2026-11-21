# Creates "Net Control" shortcuts (Start Menu + this folder) with the app icon and the
# same AppUserModelID the app sets at runtime, so pinning to the taskbar keeps the new icon.
$ErrorActionPreference = 'Stop'
$dir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $dir 'net_control.py'
$icon   = Join-Path $dir 'icon.ico'
$appId  = 'NetControl.App.1'   # must match APP_ID in net_control.py

$pyw = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = (Get-Command pythonw.exe).Source }

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class AppIdSetter {
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PROPERTYKEY { public Guid fmtid; public uint pid; }

    [StructLayout(LayoutKind.Explicit)]
    public struct PROPVARIANT {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr p;
    }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        void GetCount(out uint c);
        void GetAt(uint i, out PROPERTYKEY k);
        void GetValue(ref PROPERTYKEY k, out PROPVARIANT v);
        void SetValue(ref PROPERTYKEY k, ref PROPVARIANT v);
        void Commit();
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    static extern void SHGetPropertyStoreFromParsingName(string path, IntPtr bc, int flags,
        ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out IPropertyStore store);

    public static void Set(string lnk, string appId) {
        Guid iid = typeof(IPropertyStore).GUID;
        IPropertyStore store;
        SHGetPropertyStoreFromParsingName(lnk, IntPtr.Zero, 2 /*GPS_READWRITE*/, ref iid, out store);
        var key = new PROPERTYKEY { fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), pid = 5 };
        var val = new PROPVARIANT { vt = 31 /*VT_LPWSTR*/, p = Marshal.StringToCoTaskMemUni(appId) };
        try { store.SetValue(ref key, ref val); store.Commit(); }
        finally { Marshal.FreeCoTaskMem(val.p); Marshal.ReleaseComObject(store); }
    }

}
'@

$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$targets = @((Join-Path $startMenu 'Net Control.lnk'), (Join-Path $dir 'Net Control.lnk'))

$shell = New-Object -ComObject WScript.Shell
$shellApp = New-Object -ComObject Shell.Application
foreach ($lnk in $targets) {
    if (Test-Path $lnk) { Remove-Item $lnk -Force }
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath       = $pyw
    $s.Arguments        = "`"$script`""
    $s.WorkingDirectory = $dir
    $s.IconLocation     = "$icon,0"
    $s.Description      = 'Net Control - per-app internet control'
    $s.Save()
    [AppIdSetter]::Set($lnk, $appId)
    $item = $shellApp.Namespace((Split-Path $lnk)).ParseName((Split-Path $lnk -Leaf))
    "OK  $lnk  (AppID = $($item.ExtendedProperty('System.AppUserModel.ID')))"
}
