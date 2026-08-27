# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()

binaries = []
if sys.platform == "linux":
    # Qt 6.5+ 的 xcb 平台插件需要 libxcb-cursor；部分环境（如 ubuntu-22.04
    # runner）PyInstaller 的 ldd 分析收集不到它，导致 AppImage 无法启动。
    # 显式收集，保证 AppImage 自包含。
    try:
        import subprocess

        def _ld_so_path(name: str) -> str | None:
            table = subprocess.check_output(["ldconfig", "-p"], text=True, stderr=subprocess.DEVNULL)
            for line in table.splitlines():
                parts = line.split("=>")
                if len(parts) == 2 and name in parts[0]:
                    return parts[1].strip()
            return None

        libxcb_cursor = _ld_so_path("libxcb-cursor.so.0")
        if libxcb_cursor:
            # 必须放在 Qt 的 LibrariesPath（_internal/PyQt6/Qt6/lib）：QLibrary
            # 搜索 xcb-cursor 时走 Qt 库目录，不走 LD_LIBRARY_PATH。
            binaries.append((libxcb_cursor, "PyQt6/Qt6/lib"))
            # Qt 用 QLibrary("xcb-cursor") 找无版本 libxcb-cursor.so；
            # ubuntu 等发行版只提供 .so.0，需复制一份无版本名。
            unversioned = Path(libxcb_cursor).with_name("libxcb-cursor.so")
            if not unversioned.exists():
                import shutil
                import tempfile

                tmpdir = tempfile.mkdtemp(prefix="maw-spec-")
                unversioned = Path(tmpdir) / "libxcb-cursor.so"
                shutil.copy2(libxcb_cursor, unversioned)
            binaries.append((str(unversioned), "PyQt6/Qt6/lib"))
    except Exception as exc:  # noqa: BLE001 - 收集失败时回退 ldd 默认行为
        print(f"Warning: libxcb-cursor collection failed: {exc}", file=sys.stderr)

datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "FAQ-常见问题.txt"), "."),
    (str(ROOT / "assets" / "maw.ico"), "assets"),
    (str(ROOT / "assets" / "show.webp"), "assets"),
]

a = Analysis(
    [str(ROOT / "maw_gui.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "generate_subtitle_qwen_api",
        "maw.console",
        "maw.gui_config",
        "maw.gui_platform",
        "maw.gui_web",
        "maw.gui_workflow",
        "maw.launcher_batch",
        "maw.qwen_audio",
        "maw.segments",
        "maw.speaker",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "maw" / "pyinstaller_utf8.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MAW',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'maw.ico') if sys.platform == 'win32' else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MAW',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='MAW.app',
        icon=str(ROOT / 'assets' / 'maw.icns'),
        bundle_identifier='com.moy.mawsasrworkflow',
    )
