import sys
import shutil
import importlib.util
import platform
import os
import subprocess
from colorama import init, Fore, Style
import config

# Initialize colors
init(autoreset=True)


def print_banner():
    # Clear screen
    subprocess.run("cls" if os.name == "nt" else "clear", shell=True)

    print(
        f"{Fore.GREEN}●{Style.RESET_ALL} {Style.BRIGHT}{config.APP_NAME}{Style.RESET_ALL} {Style.DIM}v{config.APP_VERSION}{Style.RESET_ALL}"
    )
    print(f"{Style.DIM}  System Health Check Tool{Style.RESET_ALL}")
    print(f"{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")


def print_status(component: str, status: bool, details: str = "", fix_cmd: str = ""):
    """Prints a standardized status line."""
    if status:
        icon = f"{Fore.GREEN}✅{Style.RESET_ALL}"
        print(
            f" {icon} {Style.BRIGHT}{component:<20}{Style.RESET_ALL} {Fore.GREEN}Found{Style.RESET_ALL} {Style.DIM}({details}){Style.RESET_ALL}"
        )
    else:
        icon = f"{Fore.RED}❌{Style.RESET_ALL}"
        print(
            f" {icon} {Style.BRIGHT}{component:<20}{Style.RESET_ALL} {Fore.RED}MISSING{Style.RESET_ALL}"
        )
        if fix_cmd:
            print(f"    {Fore.YELLOW}➜ Fix: {Style.BRIGHT}{fix_cmd}{Style.RESET_ALL}")


def check_command(command):
    """Checks if a system command is available."""
    path = shutil.which(command)
    if path:
        return True, path
    return False, None


def check_import(module_name):
    """Checks if a Python library is installed."""
    if importlib.util.find_spec(module_name):
        return True
    return False


def check_gpu():
    """Detects available hardware acceleration."""
    import torch

    if torch.cuda.is_available():
        return True, f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
    elif torch.backends.mps.is_available():
        return True, "Apple Silicon - MPS"
    else:
        return False, "CPU Only"


def main():
    print_banner()
    print(f"\n{Fore.CYAN}🏥 Running System Health Check...{Style.RESET_ALL}\n")

    all_good = True

    # 1. Hardware Acceleration (Informational)
    print(f"{Fore.WHITE}{Style.DIM}--- Hardware Check ---{Style.RESET_ALL}")
    has_gpu, gpu_name = check_gpu()
    if has_gpu:
        print(
            f" {Fore.GREEN}🚀{Style.RESET_ALL} {Style.BRIGHT}{'Accelerator':<20}{Style.RESET_ALL} {Fore.GREEN}Active{Style.RESET_ALL} {Style.DIM}({gpu_name}){Style.RESET_ALL}"
        )
    else:
        print(
            f" {Fore.YELLOW}⚠️{Style.RESET_ALL} {Style.BRIGHT}{'Accelerator':<20}{Style.RESET_ALL} {Fore.YELLOW}None{Style.RESET_ALL} {Style.DIM}(Running on CPU - expects slower performance){Style.RESET_ALL}"
        )
    print("")

    # 2. System Dependencies
    print(f"{Fore.WHITE}{Style.DIM}--- System Dependencies ---{Style.RESET_ALL}")

    # Check FFmpeg
    has_ffmpeg, ffmpeg_path = check_command("ffmpeg")
    if has_ffmpeg:
        print_status("FFmpeg", True, ffmpeg_path)
    else:
        fix = (
            "brew install ffmpeg"
            if platform.system() == "Darwin"
            else "choco install ffmpeg"
        )
        print_status("FFmpeg", False, fix_cmd=fix)
        all_good = False

    print("")

    # 3. Python Dependencies
    print(f"{Fore.WHITE}{Style.DIM}--- Python Libraries ---{Style.RESET_ALL}")
    deps = ["torch", "whisper", "watchdog", "pyperclip", "colorama", "tqdm"]
    for dep in deps:
        if check_import(dep):
            print_status(dep, True, "Installed")
        else:
            print_status(dep, False, fix_cmd=f"pip install {dep}")
            all_good = False

    print("")

    # 4. Configuration Paths
    print(f"{Fore.WHITE}{Style.DIM}--- Configuration ---{Style.RESET_ALL}")
    if config.WHATSAPP_INTERNAL_PATH and os.path.exists(config.WHATSAPP_INTERNAL_PATH):
        print(
            f" {Fore.GREEN}📂{Style.RESET_ALL} {Style.BRIGHT}{'WhatsApp Path':<20}{Style.RESET_ALL} {Fore.GREEN}Detected{Style.RESET_ALL}"
        )
        print(f"    {Style.DIM}{config.WHATSAPP_INTERNAL_PATH}{Style.RESET_ALL}")
    else:
        print(
            f" {Fore.RED}📂{Style.RESET_ALL} {Style.BRIGHT}{'WhatsApp Path':<20}{Style.RESET_ALL} {Fore.RED}NOT FOUND{Style.RESET_ALL}"
        )
        print(
            f"    {Fore.YELLOW}➜ Fix: Open config.py and set MANUAL_PATH_OVERRIDE{Style.RESET_ALL}"
        )
        if platform.system() == "Windows":
            print(
                f"    {Style.DIM}(Make sure you have installed the WhatsApp Store Version){Style.RESET_ALL}"
            )
        all_good = False

    # Summary
    print("\n" + f"{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")
    if all_good:
        print(
            f"{Fore.GREEN}✨ System is ready! You can run 'python main.py' now.{Style.RESET_ALL}"
        )
    else:
        print(
            f"{Fore.RED}🛑 Please fix the errors above before running the transcriber.{Style.RESET_ALL}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
