# Copyright (C) 2026 Jean Paul Fernandez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import sys
import platform
import os
from typing import Optional, Dict
from colorama import init, Fore, Style
import config
import helpers

# Initialize colors
init(autoreset=True)

MODEL_REQUIREMENTS: Dict[str, float] = {
    "large": 10.0,
    "turbo": 6.0,
    "medium": 5.0,
    "small": 2.0,
    "base": 1.0,
    "tiny": 1.0,
}


def draw_bar(percent, width=20) -> str:
    """
    Creates a text-based progress bar.

    Args:
        percent (float): The percentage to fill the bar.
        width (int, optional): The width of the bar. Defaults to 20.

    Returns:
        str: The formatted progress bar.
    """
    percent = max(0.0, min(100.0, percent))
    filled = int(width * percent / 100)
    bar = "■" * filled + "·" * (width - filled)

    color = Fore.GREEN if percent < 70 else (Fore.YELLOW if percent < 90 else Fore.RED)
    return f"{color}[{bar}] {percent:.0f}%{Style.RESET_ALL}"


def suggest_model(
    total_gb: Optional[float], mem_type: Optional[str]
) -> tuple[str, float, str, float]:
    """
    Calculates usable memory based on strict safety rules.

    Args:
        total_gb (float): The total amount of memory in GB.
        mem_type (Literal['vram', 'unified', 'system', None]): The type of memory.

    Returns:
        tuple: (model_name, usable_gb, rule_desc, usage_pct)
    """
    if total_gb is None or mem_type is None:
        return "base", 0.0, "Unknown", 0.0

    # --- 1. DEFINE RULES ---
    if mem_type == "vram":
        # Leave 2GB buffer for display/OS overhead on GPU
        min_free_vram = 2.0
        usable_gb = min(
            total_gb * config.NVIDIA_VRAM_LIMIT_FACTOR, max(0, total_gb - min_free_vram)
        )
        rule_desc = (
            f"{config.NVIDIA_VRAM_LIMIT_FACTOR * 100}% of VRAM ({total_gb:.1f}GB)"
        )
    else:
        usable_gb = total_gb * config.SYSTEM_MEMORY_LIMIT_FACTOR
        rule_desc = f"{config.SYSTEM_MEMORY_LIMIT_FACTOR * 100}% of System RAM ({total_gb:.1f}GB)"

    # --- 2. SELECTION LOGIC ---
    sorted_models = sorted(MODEL_REQUIREMENTS.items(), key=lambda x: x[1], reverse=True)
    rec_model = "tiny"

    for name, size in sorted_models:
        if usable_gb > 0 and (size / usable_gb) <= 0.7:
            rec_model = name
            break

    usage_pct = (
        (MODEL_REQUIREMENTS[rec_model] / usable_gb * 100) if usable_gb > 0 else 100
    )
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
        icon = f"{Fore.GREEN}✓{Style.RESET_ALL}"
        print(
            f" {icon} {Style.BRIGHT}{component:<20}{Style.RESET_ALL} "
            f"{Fore.GREEN}Found{Style.RESET_ALL} {Style.DIM}({details}){Style.RESET_ALL}"
        )
    else:
        icon = f"{Fore.RED}✗{Style.RESET_ALL}"
        print(
            f" {icon} {Style.BRIGHT}{component:<20}{Style.RESET_ALL} "
            f"{Fore.RED}MISSING{Style.RESET_ALL}"
        )
        if fix_cmd:
            print(f"    {Fore.YELLOW}➜ Fix: {Style.BRIGHT}{fix_cmd}{Style.RESET_ALL}")


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
            f" {Fore.YELLOW}{Style.RESET_ALL} {Style.BRIGHT}{'Accelerator':<20}{Style.RESET_ALL} {Fore.YELLOW}None{Style.RESET_ALL} {Style.DIM}(Running on CPU - expects slower performance){Style.RESET_ALL}"
        )
    print("")

    total_mem, mem_type = helpers.get_memory_info()

    if total_mem:
        rec_model, usable_gb, rule_desc, usage_pct = suggest_model(total_mem, mem_type)

        print(
            f" {Fore.BLUE}💾{Style.RESET_ALL} {Style.BRIGHT}{'Memory Rule':<20}{Style.RESET_ALL} "
            f"{Fore.BLUE}{rule_desc}{Style.RESET_ALL}"
        )
        print(
            f"     {Style.DIM}Safe Allowance:      {usable_gb:.1f} GB{Style.RESET_ALL}"
        )

        current_model = config.MODEL_SIZE

        print(f"\n   {Style.BRIGHT}Optimization Analysis:{Style.RESET_ALL}")

        # Safe headroom calculation
        headroom = usable_gb - (usable_gb * (usage_pct / 100))
        print(
            f"   Recommended ({rec_model}): {draw_bar(usage_pct)} "
            f"{Style.DIM}(Leaves ~{headroom:.1f} GB Headroom){Style.RESET_ALL}"
        )

        print(f"\n   {Style.BRIGHT}Result:{Style.RESET_ALL}")
        print(
            f"   We suggest:          {Fore.GREEN}{Style.BRIGHT}'{rec_model}'{Style.RESET_ALL}"
        )
        print(f"   Your Config:         {Fore.CYAN}'{current_model}'{Style.RESET_ALL}")

        # Intelligent Suggestions
        # Fallback to 6GB if model not found in dict
        current_req = MODEL_REQUIREMENTS.get(current_model, 6.0)
        rec_req = MODEL_REQUIREMENTS.get(rec_model, 1.0)

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
                f"      {Fore.GREEN}'turbo'{Style.RESET_ALL} is significantly faster and uses less RAM."
            )

        elif current_req < rec_req:
            print(
                f"\n   {Fore.BLUE}OPTIMIZATION: Your hardware is under-utilized.{Style.RESET_ALL}"
            )
            print(
                f"      You use '{current_model}', but can handle {Fore.GREEN}'{rec_model}'{Style.RESET_ALL}."
            )
            print(
                f"      {Fore.YELLOW}➜ Switch to '{rec_model}' in config.py for better accuracy.{Style.RESET_ALL}"
            )

        elif current_model == rec_model:
            print(
                f"   {Fore.GREEN}✓ You are using the optimal model for your hardware.{Style.RESET_ALL}"
            )

    else:
        print(
            f" {Fore.YELLOW}!{Style.RESET_ALL} {Style.BRIGHT}{'Memory Check':<20}{Style.RESET_ALL} "
            f"{Fore.YELLOW}Skipped{Style.RESET_ALL} {Style.DIM}(Could not detect memory info){Style.RESET_ALL}"
        )

    print("")

    # 3. System Dependencies
    print(f"{Fore.WHITE}{Style.DIM}--- System Dependencies ---{Style.RESET_ALL}")
    has_ffmpeg, ffmpeg_path = helpers.check_command("ffmpeg")
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

    # 4. Python Dependencies
    print(f"{Fore.WHITE}{Style.DIM}--- Python Libraries ---{Style.RESET_ALL}")
    deps = ["torch", "whisper", "watchdog", "pyperclip", "colorama", "tqdm"]
    for dep in deps:
        if helpers.check_import(dep):
            print_status(dep, True, "Installed")
        else:
            print_status(dep, False, fix_cmd=f"pip install {dep}")
            all_good = False

    print("")

    # 5. Configuration Paths
    print(f"{Fore.WHITE}{Style.DIM}--- Configuration ---{Style.RESET_ALL}")
    if config.WHATSAPP_INTERNAL_PATH and os.path.exists(config.WHATSAPP_INTERNAL_PATH):
        print(
            f" {Fore.GREEN}📂{Style.RESET_ALL} {Style.BRIGHT}{'WhatsApp Path':<20}{Style.RESET_ALL} "
            f"{Fore.GREEN}Detected{Style.RESET_ALL}"
        )
        print(f"    {Style.DIM}{config.WHATSAPP_INTERNAL_PATH}{Style.RESET_ALL}")
    else:
        print(
            f" {Fore.RED}📂{Style.RESET_ALL} {Style.BRIGHT}{'WhatsApp Path':<20}{Style.RESET_ALL} "
            f"{Fore.RED}NOT FOUND{Style.RESET_ALL}"
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
            f"{Fore.GREEN}✓ System is ready! You can run 'python main.py' now.{Style.RESET_ALL}"
        )
    else:
        print(
            f"{Fore.RED}✗ Please fix the errors above before running the transcriber.{Style.RESET_ALL}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
