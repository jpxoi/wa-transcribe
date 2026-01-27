import sys
import shutil
import importlib.util
import platform
import os
import subprocess
import torch
from typing import Optional, Literal
from colorama import init, Fore, Style
import config
import helpers

# Initialize colors
init(autoreset=True)


def get_memory_info() -> tuple[
    Optional[float], Literal["vram", "unified", "system"] | None
]:
    """
    Gets the total memory information.

    Returns tuple: (total_gb, memory_type)
    memory_type can be: 'vram', 'unified', 'system', or None
    """
    try:
        # 1. Check NVIDIA VRAM
        if torch.cuda.is_available():
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return total_vram, "vram"

        # 2. Check macOS Unified Memory
        elif platform.system() == "Darwin":
            cmd = "sysctl -n hw.memsize"
            total_bytes = int(subprocess.check_output(cmd.split()).strip())
            return total_bytes / (1024**3), "unified"

        # 3. Check Linux/Windows System RAM (Fallbacks)
        # We will return None to avoid guessing wrong.
        return None, None

    except Exception:
        return None, None


def draw_bar(percent, width=20) -> str:
    """
    Creates a text-based progress bar.

    Args:
        percent (float): The percentage to fill the bar.
        width (int, optional): The width of the bar. Defaults to 20.

    Returns:
        str: The formatted progress bar.
    """
    filled = int(width * percent / 100)
    bar = "■" * filled + "·" * (width - filled)
    color = Fore.GREEN if percent < 70 else (Fore.YELLOW if percent < 90 else Fore.RED)
    return f"{color}[{bar}] {percent:.0f}%{Style.RESET_ALL}"


def suggest_model(
    total_gb, mem_type
) -> tuple[
    Literal["large", "turbo", "medium", "small", "base", "tiny"], float, str, float
]:
    """
    Calculates usable memory based on strict safety rules.

    Args:
        total_gb (float): The total amount of memory in GB.
        mem_type (Literal['vram', 'unified', 'system', None]): The type of memory.

    Returns:
        tuple: (model_name, usable_gb, rule_desc, usage_pct)
    """
    if total_gb is None:
        return "base", 0, "Unknown", 0

    # --- 1. DEFINE RULES ---
    if mem_type == "vram":
        min_free_vram = 2.0
        usable_gb = min(
            total_gb * config.NVIDIA_VRAM_LIMIT_FACTOR, total_gb - min_free_vram
        )
        rule_desc = (
            f"{config.NVIDIA_VRAM_LIMIT_FACTOR * 100}% of VRAM ({total_gb:.1f}GB)"
        )
    else:
        usable_gb = total_gb * config.SYSTEM_MEMORY_LIMIT_FACTOR
        rule_desc = f"{config.SYSTEM_MEMORY_LIMIT_FACTOR * 100}% of System RAM ({total_gb:.1f}GB)"

    # --- 2. MODEL REQUIREMENTS (Approx GB) ---
    reqs = {
        "large": 10.0,
        "turbo": 6.0,
        "medium": 5.0,
        "small": 2.0,
        "base": 1.0,
        "tiny": 1.0,
    }

    # --- 3. SELECTION LOGIC WITH OVERHEAD CALCULATION ---
    rec_model: Literal["large", "turbo", "medium", "small", "base", "tiny"] = "tiny"

    # Iterate through models to find the largest one that leaves at least 30% overhead
    candidates: list[Literal["large", "turbo", "medium", "small", "base", "tiny"]] = [
        "large",
        "turbo",
        "medium",
        "small",
        "base",
    ]
    for model_name in candidates:
        if usable_gb > 0 and (reqs[model_name] / usable_gb) <= 0.7:
            rec_model = model_name
            break

    usage_pct = (reqs[rec_model] / usable_gb) * 100 if usable_gb > 0 else 100
    return rec_model, usable_gb, rule_desc, usage_pct


def print_status(
    component: str, status: bool, details: str = "", fix_cmd: str = ""
) -> None:
    """
    Prints a standardized status line.

    Args:
        component (str): The component being checked.
        status (bool): Whether the component is found or not.
        details (str, optional): Additional details about the component. Defaults to "".
        fix_cmd (str, optional): Command to fix the issue. Defaults to "".
    """
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


def check_command(command) -> tuple[bool, Optional[str]]:
    """
    Checks if a system command is available.

    Args:
        command (str): The command to check.

    Returns:
        tuple[bool, Optional[str]]: A tuple containing a boolean indicating
        whether the command is available and the path to the command if found.
    """
    path = shutil.which(command)
    if path:
        return True, path
    return False, None


def check_import(module_name) -> bool:
    """
    Checks if a Python library is installed.

    Args:
        module_name (str): The name of the module to check.

    Returns:
        bool: True if the module is installed, False otherwise.
    """
    if importlib.util.find_spec(module_name):
        return True
    return False


def check_gpu() -> tuple[bool, Optional[str]]:
    """
    Detects available hardware acceleration.

    Returns:
        tuple[bool, Optional[str]]: A tuple containing a boolean indicating
        whether hardware acceleration is available and a string indicating
        the type of hardware acceleration if available.
    """
    import torch

    if torch.cuda.is_available():
        return True, f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
    elif torch.backends.mps.is_available():
        return True, "Apple Silicon - MPS"
    else:
        return False, "CPU Only"


def main() -> None:
    helpers.print_banner(subtitle="System Health Check Tool")
    print(f"\n{Fore.CYAN}🏥 Running System Health Check...{Style.RESET_ALL}\n")

    all_good = True

    # 1. Hardware Acceleration (Informational)
    print(f"{Fore.WHITE}{Style.DIM}--- Hardware Check ---{Style.RESET_ALL}")

    # We use get_compute_device to check IF it's not CPU
    device_type = helpers.get_compute_device()
    device_name = helpers.get_device_name()

    if device_type != "cpu":
        print(
            f" {Fore.GREEN}🚀{Style.RESET_ALL} {Style.BRIGHT}{'Accelerator':<20}{Style.RESET_ALL} {Fore.GREEN}Active{Style.RESET_ALL} {Style.DIM}({device_name}){Style.RESET_ALL}"
        )
    else:
        print(
            f" {Fore.YELLOW}⚠️{Style.RESET_ALL} {Style.BRIGHT}{'Accelerator':<20}{Style.RESET_ALL} {Fore.YELLOW}None{Style.RESET_ALL} {Style.DIM}(Running on CPU - expects slower performance){Style.RESET_ALL}"
        )
    print("")

    total_mem, mem_type = get_memory_info()

    # Model Recommendation
    if total_mem:
        rec_model, usable_gb, rule_desc, usage_pct = suggest_model(total_mem, mem_type)

        print(
            f" {Fore.BLUE}💾{Style.RESET_ALL} {Style.BRIGHT}{'Memory Rule':<20}{Style.RESET_ALL} {Fore.BLUE}{rule_desc}{Style.RESET_ALL}"
        )
        print(
            f"     {Style.DIM}Safe Allowance:      {usable_gb:.1f} GB{Style.RESET_ALL}"
        )

        current_model = config.MODEL_SIZE

        # Draw the comparison
        print(f"\n   {Style.BRIGHT}Optimization Analysis:{Style.RESET_ALL}")

        # Recommended Line
        print(
            f"   Recommended ({rec_model}): {draw_bar(usage_pct)} {Style.DIM}(Leaves ~{usable_gb - (usable_gb * (usage_pct / 100)):.1f} GB Headroom){Style.RESET_ALL}"
        )

        print(f"\n   {Style.BRIGHT}Result:{Style.RESET_ALL}")
        print(
            f"   We suggest:          {Fore.GREEN}{Style.BRIGHT}'{rec_model}'{Style.RESET_ALL}"
        )
        print(f"   Your Config:         {Fore.CYAN}'{current_model}'{Style.RESET_ALL}")

        # Intelligent Suggestions based on comparison
        req_map = {
            "tiny": 1,
            "base": 1,
            "small": 2,
            "medium": 5,
            "turbo": 6,
            "large": 10,
        }
        current_req = req_map.get(current_model, 6)

        if current_req > usable_gb:
            print(
                f"\n   {Fore.RED}CRITICAL: '{current_model}' is too large for your system.{Style.RESET_ALL}"
            )
            print(
                f"      It requires ~{current_req}GB, but you only have {usable_gb:.1f}GB safe."
            )
            print(
                f"      {Fore.YELLOW}➜ Switch to '{rec_model}' in config.py{Style.RESET_ALL}"
            )

        elif current_model == "large" and rec_model == "turbo":
            print(f"\n   {Fore.YELLOW}ADVICE: You are using 'large'.{Style.RESET_ALL}")
            print(
                f"      While your system can handle it, {Fore.GREEN}'turbo'{Style.RESET_ALL} is 8x faster"
            )
            print("      and uses 4GB less RAM with similar accuracy.")

        elif current_req < req_map.get(rec_model, 6):
            print(
                f"\n   {Fore.BLUE}OPTIMIZATION: Your hardware is under-utilized.{Style.RESET_ALL}"
            )
            print(
                f"      You are using '{current_model}', but your system can handle {Fore.GREEN}'{rec_model}'{Style.RESET_ALL}."
            )
            print(
                f"      {Fore.YELLOW}➜ Switch to '{rec_model}' in config.py for better transcription accuracy.{Style.RESET_ALL}"
            )

        elif current_model == rec_model:
            print(
                f"   {Fore.GREEN}✅ You are using the optimal model for your hardware.{Style.RESET_ALL}"
            )

    else:
        print(
            f" {Fore.YELLOW}⚠️{Style.RESET_ALL} {Style.BRIGHT}{'Memory Check':<20}{Style.RESET_ALL} {Fore.YELLOW}Skipped{Style.RESET_ALL}"
        )

    print("")

    # 2. System Dependencies
    print(f"{Fore.WHITE}{Style.DIM}--- System Dependencies ---{Style.RESET_ALL}")
    has_ffmpeg, ffmpeg_path = check_command("ffmpeg")
    if has_ffmpeg and ffmpeg_path:
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
