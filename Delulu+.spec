# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# SPECPATH is provided by PyInstaller when executing the spec file
ROOT = Path(SPECPATH).resolve()
ASSETS = ROOT / "src" / "assets"

a = Analysis(
    ["launcher_fast.py"],                 # keep simple relative entry
    pathex=[str(ROOT)],                   # allow imports from project root
    binaries=[],
    datas=[
        (str(ROOT / "src"), "src"),
        (str(ASSETS), "assets"),
    ],
    hiddenimports=[
        "launcher_fast",
        "src",
        "src.__main__",
        "src.common_imports",
        # "src.main",  # only if you really have src/main.py

        "src.models",
        "src.models.character",
        "src.models.api_config",
        "src.models.user_profile",
        "src.models.chat_models",
        "src.models.ui_models",

        "src.ui",
        "src.ui.main_window",
        "src.ui.dialogs",
        "src.ui.widgets",

        "src.core",
        "src.core.ai_interface",
        "src.core.chat_manager",

        "src.utils",
        "src.utils.file_manager",
        "src.utils.helpers",

        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",

        "requests",
        "json",

        "PIL",
        "PIL.Image",
        "PIL.ImageSequence",
        "PIL.ImageQt",

        "openai",
        "anthropic",
        "google.generativeai",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "jupyter",
        "pytest",
        "black",
        "flake8",
        "mypy",
        "PySide6.QtWebEngine",
        "PySide6.QtWebKit",
        "PySide6.QtMultimedia",
        "PySide6.QtSql",
        "PySide6.QtXml",
        "PySide6.Qt3D",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PyQt5",
        "PyQt6",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Delulu+",
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
    icon=str(ASSETS / "app_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Delulu+",
)
