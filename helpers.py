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
import subprocess
import torch
from colorama import Fore, Style
import config


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
        f"{Fore.GREEN}●{Style.RESET_ALL} {Style.BRIGHT}{config.APP_NAME}{Style.RESET_ALL} {Style.DIM}v{config.APP_VERSION}{Style.RESET_ALL}"
    )
    if subtitle:
        print(f"{Style.DIM}  {subtitle}{Style.RESET_ALL}")

    print(
        f"{Style.DIM}  © 2026 {config.DEVELOPER_NAME} (@{config.DEVELOPER_USERNAME}){Style.RESET_ALL}"
    )
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
