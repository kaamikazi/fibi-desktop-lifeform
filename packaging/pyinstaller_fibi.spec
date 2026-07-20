# PyInstaller spec for Fibi Chubi v0.30.1.
#
# Build from the project root:
#   python -m PyInstaller packaging/pyinstaller_fibi.spec --noconfirm

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent


def include_if_exists(source: Path, target: str):
    return [(str(source), target)] if source.exists() else []


datas = []
datas += include_if_exists(ROOT / "fibi" / "ui" / "assets", "fibi/ui/assets")
datas += include_if_exists(ROOT / "fibi" / "version.py", "fibi")
datas += include_if_exists(ROOT / "fibi" / "build_info.py", "fibi")
datas += include_if_exists(ROOT / "config", "config")
datas += include_if_exists(ROOT / "README.md", ".")
datas += include_if_exists(ROOT / "docs" / "GUI_MANUAL_QA_V022.md", "docs")
datas += include_if_exists(ROOT / "docs" / "RELEASE_QA_V023.md", "docs")
datas += include_if_exists(ROOT / "docs" / "RELEASE_NOTES_V024.md", "docs")
datas += include_if_exists(ROOT / "docs" / "RESET_AND_UNINSTALL.md", "docs")
datas += include_if_exists(ROOT / "docs" / "BETA_TESTER_GUIDE_V025.md", "docs")
datas += include_if_exists(ROOT / "docs" / "BETA_FEEDBACK_FLOW_V026.md", "docs")
datas += include_if_exists(ROOT / "docs" / "ISSUE_TRACKER_V026.md", "docs")
datas += include_if_exists(ROOT / "docs" / "UPDATE_PREP_V026.md", "docs")
datas += include_if_exists(ROOT / "docs" / "BROWSER_HELPER_V027.md", "docs")
datas += include_if_exists(ROOT / "docs" / "WORKFLOW_RECIPES_V028.md", "docs")
datas += include_if_exists(ROOT / "docs" / "BEGINNER_GUIDE_V029.md", "docs")
datas += include_if_exists(ROOT / "docs" / "CAPABILITIES_V029.md", "docs")
datas += include_if_exists(ROOT / "docs" / "COMMANDS_V029.md", "docs")
datas += include_if_exists(ROOT / "docs" / "SAFETY_MODEL_V029.md", "docs")
datas += include_if_exists(ROOT / "docs" / "MEMORY_REVIEW_CENTER_V030.md", "docs")
datas += include_if_exists(ROOT / "docs" / "MEMORY_PRIVACY_V030.md", "docs")
datas += include_if_exists(ROOT / "docs" / "GEMINI_PROVIDER_V0301.md", "docs")
datas += include_if_exists(ROOT / "docs" / "CLOUD_CONTEXT_PRIVACY_V0301.md", "docs")
datas += include_if_exists(ROOT / "updates", "updates")
datas += include_if_exists(ROOT / "packaging" / "README.md", "packaging")
datas += include_if_exists(ROOT / "packaging" / "installer_notes.md", "packaging")
datas += include_if_exists(ROOT / "packaging" / "release_checklist.md", "packaging")

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "google.genai",
        "google.genai.types",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "data",
        "voice_models",
        ".git",
        ".pytest_cache",
        "torch",
        "torchaudio",
        "torchvision",
        "transformers",
        "sentence_transformers",
        "rvc_python",
        "pandas",
        "pyarrow",
        "scipy",
        "sklearn",
        "av",
        "onnxruntime",
        "yt_dlp",
        "openpyxl",
        "lxml",
        "matplotlib",
    ],
    noarchive=False,
)


def keep_toc_item(item):
    destination = item[0].replace("\\", "/").lower()
    parts = set(destination.split("/"))
    if {"tests", "__pycache__", ".pytest_cache"} & parts:
        return False
    if destination.endswith((".env", ".pth", ".index")):
        return False
    if "/voice_models/" in destination or destination.startswith("voice_models/"):
        return False
    return True


a.datas = [item for item in a.datas if keep_toc_item(item)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Fibi Chubi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Fibi Chubi",
)
