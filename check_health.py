import sys
import shutil
import importlib.util
from config import WHATSAPP_INTERNAL_PATH


def check_command(command):
    """Checks if a system command is available."""
    if shutil.which(command):
        print(f"✅ Found system dependency: {command}")
        return True
    else:
        print(f"❌ MISSING system dependency: {command}")
        return False


def check_import(module_name):
    """Checks if a Python library is installed."""
    if importlib.util.find_spec(module_name):
        print(f"✅ Found Python library: {module_name}")
        return True
    else:
        print(f"❌ MISSING Python library: {module_name}")
        return False


def main():
    print("🏥 Running Health Check...\n")

    all_good = True

    # 1. Check System Dependencies (Critical for Whisper)
    if not check_command("ffmpeg"):
        print("   -> ⚠️  FFmpeg is required for Whisper to process audio.")
        print("   -> macOS: brew install ffmpeg")
        print("   -> Windows: choco install ffmpeg (or download from website)")
        all_good = False

    # 2. Check Python Dependencies
    deps = ["torch", "whisper", "watchdog", "pyperclip"]
    for dep in deps:
        if not check_import(dep):
            all_good = False

    # 3. Check Configuration Paths
    print("\n📂 Checking Paths:")
    if WHATSAPP_INTERNAL_PATH:
        print(f"✅ WhatsApp Path detected: {WHATSAPP_INTERNAL_PATH}")
    else:
        print("❌ WhatsApp Path NOT detected.")
        print("   -> Please edit config.py and set MANUAL_PATH_OVERRIDE")
        all_good = False

    # Summary
    print("-" * 30)
    if all_good:
        print("🚀 System is ready! You can run 'python main.py' now.")
    else:
        print("🛑 Please fix the errors above before running the transcriber.")
        sys.exit(1)


if __name__ == "__main__":
    main()
