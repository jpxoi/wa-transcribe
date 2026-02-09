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
import json
import platform
from app import utils
from colorama import Style, Fore
from pathlib import Path
from typing import Optional, Dict, Any, List

# --- APP IDENTITY ---
APP_NAME = "wa-transcriber"
APP_VERSION = "1.1.0"
DEVELOPER_NAME = "Jean Paul Fernandez"
DEVELOPER_USERNAME = "jpxoi"

# --- OS-SPECIFIC DATA PATHS ---
HOME_DIR: Path = Path.home()
SYSTEM: str = platform.system()


def get_app_data_dir() -> Path:
    """Returns the path for app data (Config, DB, Logs) under ~/.wa-transcriber."""
    app_dir: Path = HOME_DIR / ".wa-transcriber"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DATA_DIR: Path = get_app_data_dir()
CONFIG_FILE_PATH: Path = APP_DATA_DIR / "config.json"
DB_PATH: Path = APP_DATA_DIR / "history.db"

# --- LOGS ---
APP_LOGS_DIR: Path = APP_DATA_DIR / "logs" / "app"
TRANSCRIBED_AUDIO_LOGS_DIR: Path = APP_DATA_DIR / "logs" / "transcribed_audio"

# Ensure log directories exist
APP_LOGS_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIBED_AUDIO_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# --- CONSTANTS ---
KNOWN_MODELS: List[str] = [
    "tiny.pt",
    "base.pt",
    "small.pt",
    "medium.pt",
    "large-v3.pt",
    "turbo.pt",
    "tiny.en.pt",
    "base.en.pt",
    "small.en.pt",
    "medium.en.pt",
]

# --- DEFAULTS ---
DEFAULT_CONFIG: Dict[str, Any] = {
    "MODEL_SIZE": "turbo",
    "TRANSCRIPTION_LANGUAGE": None,
    "SCAN_LOOKBACK_ENABLED": True,
    "SCAN_LOOKBACK_HOURS": 1,
    "MODEL_CLEANUP_ENABLED": True,
    "MODEL_RETENTION_DAYS": 3,
    "ENABLE_MPS_FP16": False,
    "SYSTEM_MEMORY_LIMIT_FACTOR": 0.5,
    "NVIDIA_VRAM_LIMIT_FACTOR": 0.7,
    "FILE_READY_TIMEOUT": 10,
    "MANUAL_PATH_OVERRIDE": None,
}

# --- GLOBAL VARIABLES (Populated by load_configuration) ---
MODEL_SIZE: str = DEFAULT_CONFIG["MODEL_SIZE"]
TRANSCRIPTION_LANGUAGE: Optional[str] = DEFAULT_CONFIG["TRANSCRIPTION_LANGUAGE"]
SCAN_LOOKBACK_ENABLED: bool = DEFAULT_CONFIG["SCAN_LOOKBACK_ENABLED"]
SCAN_LOOKBACK_HOURS: int = DEFAULT_CONFIG["SCAN_LOOKBACK_HOURS"]
MODEL_CLEANUP_ENABLED: bool = DEFAULT_CONFIG["MODEL_CLEANUP_ENABLED"]
MODEL_RETENTION_DAYS: int = DEFAULT_CONFIG["MODEL_RETENTION_DAYS"]
ENABLE_MPS_FP16: bool = DEFAULT_CONFIG["ENABLE_MPS_FP16"]
SYSTEM_MEMORY_LIMIT_FACTOR: float = DEFAULT_CONFIG["SYSTEM_MEMORY_LIMIT_FACTOR"]
NVIDIA_VRAM_LIMIT_FACTOR: float = DEFAULT_CONFIG["NVIDIA_VRAM_LIMIT_FACTOR"]
FILE_READY_TIMEOUT: int = DEFAULT_CONFIG["FILE_READY_TIMEOUT"]
MANUAL_PATH_OVERRIDE: Optional[str] = DEFAULT_CONFIG["MANUAL_PATH_OVERRIDE"]
WHATSAPP_INTERNAL_PATH: Optional[str] = None  # Calculated at runtime


def show_config() -> None:
    """Prints the current configuration with improved formatting and grouping."""
    utils.print_banner("Current Configuration")

    def _fmt_bool(val: bool) -> str:
        """Helper to colorize booleans."""
        return (
            f"{Fore.GREEN}Enabled{Style.RESET_ALL}"
            if val
            else f"{Style.DIM}Disabled{Style.RESET_ALL}"
        )

    def _fmt_val(val: Any) -> str:
        """Helper to format generic values nicely."""
        if val is None:
            return f"{Fore.YELLOW}Auto / None{Style.RESET_ALL}"
        if isinstance(val, bool):
            return _fmt_bool(val)
        return f"{Fore.CYAN}{val}{Style.RESET_ALL}"

    def _print_row(key: str, val: Any):
        print(f"   {Style.DIM}•{Style.RESET_ALL} {key:<28} {_fmt_val(val)}")

    # --- Group 1: Core Transcription ---
    print(f" {Fore.WHITE}{Style.BRIGHT}🤖 Core Settings{Style.RESET_ALL}")
    _print_row("Model Size", MODEL_SIZE)
    _print_row("Transcription Language", TRANSCRIPTION_LANGUAGE)
    _print_row("File Ready Timeout", f"{FILE_READY_TIMEOUT}s")

    # --- Group 2: Features & Cleanup ---
    print(f"\n {Fore.WHITE}{Style.BRIGHT}🧹 Automation & Cleanup{Style.RESET_ALL}")
    _print_row("Scan Lookback", SCAN_LOOKBACK_ENABLED)
    if SCAN_LOOKBACK_ENABLED:
        _print_row("   Lookback Depth", f"{SCAN_LOOKBACK_HOURS} hours")

    _print_row("Model Cleanup", MODEL_CLEANUP_ENABLED)
    if MODEL_CLEANUP_ENABLED:
        _print_row("   Retention Period", f"{MODEL_RETENTION_DAYS} days")

    # --- Group 3: Hardware & Performance ---
    print(f"\n {Fore.WHITE}{Style.BRIGHT}⚡ Hardware Limits{Style.RESET_ALL}")
    _print_row("System Memory Limit", f"{int(SYSTEM_MEMORY_LIMIT_FACTOR * 100)}%")
    _print_row("NVIDIA VRAM Limit", f"{int(NVIDIA_VRAM_LIMIT_FACTOR * 100)}%")
    _print_row("Apple MPS FP16", ENABLE_MPS_FP16)

    # --- Group 4: Storage ---
    print(f"\n {Fore.WHITE}{Style.BRIGHT}📂 Paths{Style.RESET_ALL}")

    path_display = (
        MANUAL_PATH_OVERRIDE if MANUAL_PATH_OVERRIDE else "Auto-Detected (Default)"
    )
    path_color = Fore.CYAN if MANUAL_PATH_OVERRIDE else Fore.YELLOW

    print(
        f"   {Style.DIM}•{Style.RESET_ALL} {'WhatsApp Media Path':<28} {path_color}{path_display}{Style.RESET_ALL}"
    )

    # --- Footer ---
    print(f"{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")
    print(
        f" {Fore.GREEN}➜ To Change:{Style.RESET_ALL}     Run {Style.BRIGHT}wa-transcriber setup{Style.RESET_ALL}"
    )
    print(
        f" {Fore.GREEN}➜ Config File:{Style.RESET_ALL} {Style.DIM}{CONFIG_FILE_PATH}{Style.RESET_ALL}\n"
    )


def load_configuration() -> bool:
    """
    Loads config from JSON. Returns True if successful, False if file is missing (First Run).
    """
    # Use 'global' to update module-level variables
    global \
        MODEL_SIZE, \
        TRANSCRIPTION_LANGUAGE, \
        SCAN_LOOKBACK_ENABLED, \
        SCAN_LOOKBACK_HOURS, \
        MODEL_CLEANUP_ENABLED, \
        MODEL_RETENTION_DAYS, \
        ENABLE_MPS_FP16, \
        SYSTEM_MEMORY_LIMIT_FACTOR, \
        NVIDIA_VRAM_LIMIT_FACTOR, \
        FILE_READY_TIMEOUT, \
        MANUAL_PATH_OVERRIDE

    if not CONFIG_FILE_PATH.exists():
        return False

    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            user_config = json.load(f)

        # safely get keys or fallback to default
        MODEL_SIZE = user_config.get("MODEL_SIZE", DEFAULT_CONFIG["MODEL_SIZE"])
        TRANSCRIPTION_LANGUAGE = user_config.get(
            "TRANSCRIPTION_LANGUAGE", DEFAULT_CONFIG["TRANSCRIPTION_LANGUAGE"]
        )
        SCAN_LOOKBACK_ENABLED = user_config.get(
            "SCAN_LOOKBACK_ENABLED", DEFAULT_CONFIG["SCAN_LOOKBACK_ENABLED"]
        )
        SCAN_LOOKBACK_HOURS = user_config.get(
            "SCAN_LOOKBACK_HOURS", DEFAULT_CONFIG["SCAN_LOOKBACK_HOURS"]
        )
        MODEL_CLEANUP_ENABLED = user_config.get(
            "MODEL_CLEANUP_ENABLED", DEFAULT_CONFIG["MODEL_CLEANUP_ENABLED"]
        )
        MODEL_RETENTION_DAYS = user_config.get(
            "MODEL_RETENTION_DAYS", DEFAULT_CONFIG["MODEL_RETENTION_DAYS"]
        )
        ENABLE_MPS_FP16 = user_config.get(
            "ENABLE_MPS_FP16", DEFAULT_CONFIG["ENABLE_MPS_FP16"]
        )
        SYSTEM_MEMORY_LIMIT_FACTOR = user_config.get(
            "SYSTEM_MEMORY_LIMIT_FACTOR", DEFAULT_CONFIG["SYSTEM_MEMORY_LIMIT_FACTOR"]
        )
        NVIDIA_VRAM_LIMIT_FACTOR = user_config.get(
            "NVIDIA_VRAM_LIMIT_FACTOR", DEFAULT_CONFIG["NVIDIA_VRAM_LIMIT_FACTOR"]
        )
        FILE_READY_TIMEOUT = user_config.get(
            "FILE_READY_TIMEOUT", DEFAULT_CONFIG["FILE_READY_TIMEOUT"]
        )
        MANUAL_PATH_OVERRIDE = user_config.get(
            "MANUAL_PATH_OVERRIDE", DEFAULT_CONFIG["MANUAL_PATH_OVERRIDE"]
        )
        return True
    except Exception as e:
        print(f"⚠ Error loading config: {e}")
        return False


def save_configuration(new_config: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(new_config, f, indent=4)
    except Exception as e:
        print(f"change_this Error saving config: {e}")


def find_default_whatsapp_path() -> Optional[str]:
    """
    Attempts to locate the WhatsApp Media folder based on OS defaults.
    Returns the path string if found, otherwise None.
    """
    detected_path = None

    if SYSTEM == "Darwin":
        _mac_store = (
            HOME_DIR
            / "Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media"
        )
        _mac_direct = HOME_DIR / "Library/Application Support/WhatsApp/Media"
        if _mac_store.exists():
            detected_path = str(_mac_store)
        elif _mac_direct.exists():
            detected_path = str(_mac_direct)

    elif SYSTEM == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        _win_store = os.path.join(
            local_app_data,
            "Packages",
            "5319275A.WhatsAppDesktop_cv1g1gvanyjgm",
            "LocalState",
            "shared",
            "transfers",
        )
        _win_legacy = os.path.join(local_app_data, "WhatsApp", "Media")

        if os.path.exists(_win_store):
            detected_path = _win_store
        elif os.path.exists(_win_legacy):
            detected_path = _win_legacy

    return detected_path


def detect_whatsapp_path() -> None:
    """
    Sets the WHATSAPP_INTERNAL_PATH global.
    Prioritizes Manual Override, then falls back to Auto-Detect.
    """
    global WHATSAPP_INTERNAL_PATH

    # 1. Check Manual Override
    if MANUAL_PATH_OVERRIDE and os.path.exists(MANUAL_PATH_OVERRIDE):
        WHATSAPP_INTERNAL_PATH = MANUAL_PATH_OVERRIDE
        return

    # 2. Check Auto-Detect
    WHATSAPP_INTERNAL_PATH = find_default_whatsapp_path()
