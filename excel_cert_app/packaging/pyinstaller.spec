# PyInstaller spec — build a one-dir Windows bundle including exam content.
# Build:  pyinstaller packaging/pyinstaller.spec
from pathlib import Path

block_cipher = None
ROOT = Path(".").resolve()

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ("content", "content"),          # projects + solutions + tasks
        ("app/ui/theme.qss", "app/ui"),
        ("app/db/schema.sql", "app/db"),
    ],
    hiddenimports=[
        "win32com.client", "pythoncom", "pywintypes", "win32gui", "win32process",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="SimulateurExcel",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="SimulateurExcel")
