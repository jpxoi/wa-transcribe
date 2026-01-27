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
import platform
from pathlib import Path
from typing import List, Optional

# ==============================================================================
#   👇 USER CONFIGURATION (EDIT THESE SETTINGS)
# ==============================================================================

# --- 1. MODEL SELECTION ---
# Controls the balance between speed and accuracy.
# Options:
#   - "tiny"            : Less accurate, but faster and uses less memory.
#   - "base" / "small"  : Fast, low memory. Good for older laptops.
#   - "medium"          : (Recommended) Best balance for M1/M2/M3 Macs.
#   - "large-v3"        : Maximum accuracy, but slower and uses ~4GB VRAM.
#   - "turbo"           : New high-speed model (very fast, good accuracy).
MODEL_SIZE: str = "medium"


# --- 2. MANUAL PATH OVERRIDE (OPTIONAL) ---
# If the script cannot find your WhatsApp folder automatically, paste the full path here.
# Example: "/Users/jdoe/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media"
# Leave as None to use auto-detection.
MANUAL_PATH_OVERRIDE: Optional[str] = None


# ==============================================================================
#   ⛔️ SYSTEM CONFIGURATION (DO NOT EDIT BELOW THIS LINE)
#   Internal logic for path detection, logging, and OS handling.
# ==============================================================================

# --- SYSTEM SETTINGS ---
HOME_DIR: str = str(Path.home())
CURRENT_OS: str = platform.system()

# --- LOGGING PATHS ---
# Saves logs in a folder named 'transcribed_audio_logs' relative to this script.
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER_NAME: str = "transcribed_audio_logs"
LOG_FOLDER_PATH: str = os.path.join(BASE_DIR, LOG_FOLDER_NAME)

# --- WHATSAPP PATH AUTO-DETECTION ---
WHATSAPP_INTERNAL_PATH: Optional[str] = None

# 1. Check if user provided a manual override
if MANUAL_PATH_OVERRIDE and os.path.exists(MANUAL_PATH_OVERRIDE):
    WHATSAPP_INTERNAL_PATH = MANUAL_PATH_OVERRIDE

# 2. If no override, attempt auto-detection based on OS
elif CURRENT_OS == "Darwin":  # macOS
    _mac_store_path: str = os.path.join(
        HOME_DIR,
        "Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media",
    )
    _mac_direct_path: str = os.path.join(
        HOME_DIR, "Library/Application Support/WhatsApp/Media"
    )

    if os.path.exists(_mac_store_path):
        WHATSAPP_INTERNAL_PATH = _mac_store_path
    elif os.path.exists(_mac_direct_path):
        WHATSAPP_INTERNAL_PATH = _mac_direct_path

elif CURRENT_OS == "Windows":
    # Windows paths vary significantly by installation method (Store vs. Exe).
    # Windows users generally need to use MANUAL_PATH_OVERRIDE.
    WHATSAPP_INTERNAL_PATH = None

# --- CONSTANTS ---
# Official Model List (Updated from OpenAI Docs)
KNOWN_MODELS: List[str] = [
    # Multilingual Models
    "tiny.pt",
    "base.pt",
    "small.pt",
    "medium.pt",
    "large.pt",
    "large-v1.pt",
    "large-v2.pt",
    "large-v3.pt",
    "turbo.pt",
    # English-only Models
    "tiny.en.pt",
    "base.en.pt",
    "small.en.pt",
    "medium.en.pt",
]
