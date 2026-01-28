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

import os
import sys
import shutil
import torch
import platform
import subprocess
import importlib.util
from app import config
from pathlib import Path
from collections import deque
from colorama import Fore, Style
from typing import Optional, Literal, cast


def clear_screen():
    """Clears the terminal screen cross-platform."""
    subprocess.run("cls" if os.name == "nt" else "clear", shell=True)


def set_window_title(title: str):
    """
    Sets the terminal window title.

    Args:
        title (str): The title to set.
    """
    if os.name == "nt":  # Windows
        subprocess.run(f"title {title}", shell=True)
    else:  # macOS / Linux
        sys.stdout.write(f"\x1b]2;{title}\x07")


def print_banner(subtitle: str = ""):
    """
    Prints the standardized ASCII banner.

    Args:
        subtitle (str, optional): A subtitle to display below the main title. Defaults to "".
    """
    clear_screen()
    set_window_title(config.APP_NAME)

    print(
        f"{Fore.GREEN}●{Style.RESET_ALL} {Style.BRIGHT}{config.APP_NAME}{Style.RESET_ALL} "
        f"{Style.DIM}v{config.APP_VERSION}{Style.RESET_ALL}"
    )
    if subtitle:
        print(f"{Style.DIM}  {subtitle}{Style.RESET_ALL}")

    footer = f"© 2026 {config.DEVELOPER_NAME} (@{config.DEVELOPER_USERNAME})"
    print(f"{Style.DIM}  {footer}{Style.RESET_ALL}")
    print(f"{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")


def get_compute_device() -> str:
    """
    Smartly selects the best hardware accelerator available.

    Returns:
        str: "mps" (Mac), "cuda" (NVIDIA), or "cpu".
    """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_device_name() -> str:
    """Returns a human-readable name for the active accelerator (for UI)."""
    if torch.cuda.is_available():
        return f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
    if torch.backends.mps.is_available():
        return "Apple Silicon (MPS)"
    return "CPU Only"


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
    return importlib.util.find_spec(module_name) is not None


def get_memory_info() -> tuple[
    Optional[float], Literal["vram", "unified", "system"] | None
]:
    """
    Gets the total memory information.

    Returns:
        tuple: (total_gb, memory_type)
    """
    try:
        # 1. Check NVIDIA VRAM
        if torch.cuda.is_available():
            # torch.cuda.get_device_properties(0).total_memory returns bytes
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return total_vram, "vram"

        # 2. Check macOS Unified Memory
        elif platform.system() == "Darwin":
            cmd = "sysctl -n hw.memsize"
            total_bytes = int(subprocess.check_output(cmd.split()).strip())
            return total_bytes / (1024**3), "unified"

        # 3. Check Linux System RAM
        elif platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb_value = int(line.split()[1])
                        return kb_value / (1024**2), "system"

        # 4. Windows Fallback
        return None, None

    except Exception:
        return None, None


def show_logs(
    type: Literal["app", "transcribed_audio"], lines_to_show: int = 50
) -> None:
    """
    Finds the most recent log file and prints the last N lines.
    """
    print_banner("Recent Logs")

    if type == "app":
        log_dir = config.APP_LOGS_DIR
    elif type == "transcribed_audio":
        log_dir = config.TRANSCRIBED_AUDIO_LOGS_DIR
    else:
        raise ValueError(f"Invalid log type: {type}")

    # 1. Find all log files matching the pattern
    list_of_files: list[Path] = list(log_dir.glob("*_daily.log"))

    if not list_of_files:
        print(f"{Fore.YELLOW}⚠ No log files found in:{Style.RESET_ALL}")
        print(f"  {log_dir}")
        return

    # 2. Get the latest file (Sort by modification time)
    latest_file = cast(Path, max(list_of_files, key=os.path.getmtime))
    filename = latest_file.name

    print(
        f"{Style.DIM}Reading latest log file: {Fore.CYAN}{filename}{Style.RESET_ALL}\n"
    )

    # 3. Read only the last N lines efficiently
    try:
        with open(latest_file, "r", encoding="utf-8", errors="replace") as f:
            last_lines = deque(f, maxlen=lines_to_show)

            if not last_lines:
                print(f"{Style.DIM}(Log file is empty){Style.RESET_ALL}")

            for line in last_lines:
                # Add a subtle border for readability
                print(f"{Style.DIM}│{Style.RESET_ALL} {line.strip()}")

    except Exception as e:
        print(f"{Fore.RED}Error reading log file: {e}{Style.RESET_ALL}")

    # 4. Footer
    print(f"\n{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")
    print(
        f"{Fore.GREEN}➜ Full logs location:{Style.RESET_ALL} {Style.BRIGHT}{config.TRANSCRIBED_AUDIO_LOGS_DIR}{Style.RESET_ALL}"
    )
