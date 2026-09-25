"""
build_exe.py - Standalone Executable Builder for Swift-ProSys Image Encryptor.
Builds a single, standalone Windows executable (.exe) with embedded icon,
dark theme styling, and brand logos.
"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(BASE_DIR, "Swift_Prosys.ico")
LOGO_PREVIEW = os.path.join(BASE_DIR, "Swift-ProSys-Logo-2026-1-removebg-preview.png")
LOGO_FALLBACK = os.path.join(BASE_DIR, "Swift-ProSys-Logo.png")
ENTRY_POINT = os.path.join(BASE_DIR, "encryptor_app.py")
EXE_NAME = "SwiftProSys_ImageEncryptor"


def _kill_running_instances():
    """Ensure no previous instance of the .exe is running and locking the file."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", f"{EXE_NAME}.exe", "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


def build():
    print("=" * 60)
    print(" BUILDING SWIFT-PROSYS IMAGE ENCRYPTOR STANDALONE EXE")
    print("=" * 60)

    # 1. Close any running instances locking dist\SwiftProSys_ImageEncryptor.exe
    _kill_running_instances()

    # 2. Validate prerequisites
    if not os.path.exists(ENTRY_POINT):
        print(f"Error: Entry point not found: {ENTRY_POINT}")
        sys.exit(1)
    if not os.path.exists(ICO_PATH):
        print(f"Warning: Icon file not found: {ICO_PATH}")

    # Check if target dist exe is still locked
    dist_exe = os.path.join(BASE_DIR, "dist", f"{EXE_NAME}.exe")
    if os.path.exists(dist_exe):
        try:
            with open(dist_exe, "a+b"):
                pass
        except PermissionError:
            print(f"[ERROR] '{dist_exe}' is currently locked by another program.")
            print("Please close any open instances of the Image Encryptor and try again.")
            sys.exit(1)

    # 3. Build PyInstaller command line
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={EXE_NAME}",
    ]

    if os.path.exists(ICO_PATH):
        cmd.append(f"--icon={ICO_PATH}")

    # --add-data fails the whole build if its source file doesn't exist
    # (e.g. the "-removebg-preview" logo variant is optional and may not
    # be present next to the script), so only bundle assets that are
    # actually there. theme_config.py already falls back gracefully at
    # runtime when one of these is missing.
    for data_file in (ICO_PATH, LOGO_PREVIEW, LOGO_FALLBACK):
        if os.path.exists(data_file):
            cmd.append(f"--add-data={data_file};.")
        else:
            print(f"Note: skipping missing bundled asset (not required): {data_file}")

    cmd += [
        "--hidden-import=cryptography",
        "--hidden-import=PyQt6",
        "--hidden-import=requests",
        # Pillow loads several image-format plugins (JPEG 2000/openjpeg,
        # WebP, etc.) as dynamic binary libraries at runtime, which
        # PyInstaller's default import scan can miss - this ensures every
        # one of Pillow's binaries/data/submodules is bundled so JP2/WebP
        # compression works reliably in the packaged exe on any machine.
        "--collect-all=PIL",
        ENTRY_POINT
    ]

    print("Running command:")
    print(" ".join(cmd))
    print("-" * 60)

    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print("\n[FAILED] PyInstaller build failed with exit code:", result.returncode)
        sys.exit(result.returncode)

    dist_exe = os.path.join(BASE_DIR, "dist", f"{EXE_NAME}.exe")
    if os.path.exists(dist_exe):
        size_mb = os.path.getsize(dist_exe) / (1024 * 1024)
        print("\n" + "=" * 60)
        print("[SUCCESS] Build completed successfully!")
        print(f"Executable: {dist_exe}")
        print(f"Size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\n[WARNING] dist exe not found at expected location:", dist_exe)


if __name__ == "__main__":
    build()