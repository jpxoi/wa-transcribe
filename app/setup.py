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
import shutil
import questionary
from app import config, utils
from questionary import Choice
from colorama import Fore, Style


MODEL_REQUIREMENTS = {
    "large": 10.0,
    "turbo": 6.0,
    "medium": 5.0,
    "small": 2.0,
    "base": 1.0,
    "tiny": 1.0,
}


def reset_application(interactive: bool = True) -> None:
    """
    Deletes the application data directory after user confirmation.

    Args:
        interactive (bool): Whether to prompt for confirmation. Defaults to True.
    """
    utils.print_banner("Reset Application")

    if interactive:
        if not questionary.confirm(
            "Are you sure you want to reset all application data? This cannot be undone.",
            default=False,
        ).ask():
            return

    app_data_dir = os.path.expanduser(config.APP_DATA_DIR)

    try:
        if os.path.exists(app_data_dir):
            shutil.rmtree(app_data_dir)
        print(f"{Fore.GREEN}Successfully reset application data.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Failed to reset application data: {str(e)}{Style.RESET_ALL}")


def suggest_best_model() -> str:
    """
    Analyzes system memory to suggest the best Whisper model.
    Returns the name of the model (e.g. 'medium', 'turbo').
    """
    total_gb, mem_type = utils.get_memory_info()

    # Fallback if detection fails
    if total_gb is None or mem_type is None:
        return "turbo"

    # Calculate usable memory based on config defaults
    if mem_type == "vram":
        # GPU Rule: Limit factor OR (Total - 2GB overhead), whichever is smaller
        min_free_vram = 2.0
        usable_gb = min(
            total_gb * config.NVIDIA_VRAM_LIMIT_FACTOR, max(0, total_gb - min_free_vram)
        )
    else:
        # System RAM Rule: Simple multiplier
        usable_gb = total_gb * config.SYSTEM_MEMORY_LIMIT_FACTOR

    # Find the largest model that fits safely (using the 0.7 safety ratio from diagnostics)
    sorted_models = sorted(MODEL_REQUIREMENTS.items(), key=lambda x: x[1], reverse=True)

    for name, size in sorted_models:
        if usable_gb > 0 and (size / usable_gb) <= 0.7:
            return name

    return "tiny"  # Absolute fallback


def run_interactive_wizard():
    utils.print_banner("Setup Wizard")

    print(
        f"📂 Configuration will be saved to: {Style.DIM}{os.path.expanduser(config.CONFIG_FILE_PATH)}{Style.RESET_ALL}\n"
    )

    # Start with default config
    new_config = config.DEFAULT_CONFIG.copy()

    # --- SECTION 1: CORE SETTINGS (Everyone needs these) ---

    # 1. Model Selection (Smart Suggestion)
    suggested_model = suggest_best_model()

    def get_desc(model_name, base_desc):
        if model_name == suggested_model:
            return f"SUGGESTED - {base_desc}"
        return base_desc

    print(
        f"{Style.DIM}Based on your hardware, we have selected a default below.{Style.RESET_ALL}"
    )

    new_config["MODEL_SIZE"] = questionary.select(
        "Which transcription model would you like to use?",
        choices=[
            Choice(
                "turbo",
                description=get_desc(
                    "turbo", "Recommended - Best balance of speed and accuracy"
                ),
            ),
            Choice(
                "large",
                description=get_desc(
                    "large", "Maximum accuracy, highest resource usage"
                ),
            ),
            Choice(
                "medium",
                description=get_desc("medium", "High accuracy, moderate speed"),
            ),
            Choice("small", description=get_desc("small", "Good accuracy, fast")),
            Choice("base", description=get_desc("base", "Low accuracy, very fast")),
            Choice("tiny", description=get_desc("tiny", "Lowest accuracy, fastest")),
        ],
        default=suggested_model,  # Sets the cursor to the calculated best fit
        instruction="Use arrow keys to navigate and Enter to select.",
    ).ask()

    # 2. Language
    lang_choice = questionary.text(
        "Forced Language (Leave empty for Auto-Detect):",
        instruction="(e.g. 'en', 'es')",
    ).ask()

    new_config["TRANSCRIPTION_LANGUAGE"] = (
        lang_choice.strip() if lang_choice.strip() else None
    )

    # 3. WhatsApp Path (Smart Detection)
    detected_path = config.find_default_whatsapp_path()

    if detected_path:
        print(
            f"\n🔍 We detected your WhatsApp folder at:\n   {Fore.CYAN}{detected_path}{Style.RESET_ALL}\n"
        )

        is_correct = questionary.confirm(
            "Is this the correct folder?", default=True
        ).ask()

        if is_correct:
            # User accepted auto-detect; we leave override as None so it stays dynamic
            new_config["MANUAL_PATH_OVERRIDE"] = None
        else:
            # User wants to change it
            new_config["MANUAL_PATH_OVERRIDE"] = questionary.path(
                "Please enter the absolute path to your WhatsApp Media folder:",
                only_directories=True,
                validate=lambda p: os.path.exists(p) or "Path does not exist!",
            ).ask()

    else:
        # Auto-detect failed
        print(
            f"{Fore.YELLOW}⚠  Could not automatically locate WhatsApp Media folder.{Style.RESET_ALL}"
        )
        new_config["MANUAL_PATH_OVERRIDE"] = questionary.path(
            "Please manually enter the path to your WhatsApp Media folder:",
            only_directories=True,
            validate=lambda p: os.path.exists(p) or "Path does not exist!",
        ).ask()

    # --- SECTION 2: ADVANCED SETTINGS (Optional) ---

    configure_advanced = questionary.confirm(
        "Do you want to configure advanced settings?",
        default=False,
    ).ask()

    if configure_advanced:
        # A. Scan Lookback
        new_config["SCAN_LOOKBACK_ENABLED"] = questionary.confirm(
            "Enable 'Scan Lookback' on startup? (Checks for missed files)", default=True
        ).ask()

        if new_config["SCAN_LOOKBACK_ENABLED"]:
            new_config["SCAN_LOOKBACK_HOURS"] = int(
                questionary.text(
                    "How many hours back should we scan?",
                    default="1",
                    validate=lambda text: text.isdigit() or "Please enter a number",
                ).ask()
            )

        # B. Model Cleanup
        new_config["MODEL_CLEANUP_ENABLED"] = questionary.confirm(
            "Enable Model Cleanup? (Deletes unused models to save disk space)",
            default=True,
        ).ask()

        if new_config["MODEL_CLEANUP_ENABLED"]:
            new_config["MODEL_RETENTION_DAYS"] = int(
                questionary.text(
                    "Delete models unused for X days:",
                    default="3",
                    validate=lambda text: text.isdigit() or "Please enter a number",
                ).ask()
            )

        # C. Hardware / Performance
        new_config["SYSTEM_MEMORY_LIMIT_FACTOR"] = float(
            questionary.select(
                "System Memory Usage Limit:",
                choices=[
                    Choice("0.3", description="Eco (30%) - minimal impact"),
                    Choice("0.5", description="Safe (50%) - Recommended"),
                    Choice("0.9", description="Aggressive (90%) - Max speed"),
                ],
            ).ask()
        )

        # Only ask VRAM if on a relevant system, or just ask it generally
        new_config["NVIDIA_VRAM_LIMIT_FACTOR"] = float(
            questionary.select(
                "GPU VRAM Usage Limit (NVIDIA only):",
                choices=[
                    Choice("0.3", description="Eco (30%)"),
                    Choice("0.7", description="Standard (70%) - Recommended"),
                    Choice("0.9", description="Max (90%)"),
                ],
            ).ask()
        )

    # --- SAVE ---
    if questionary.confirm(
        f"Save these settings to {config.CONFIG_FILE_PATH}?", default=True
    ).ask():
        config.save_configuration(new_config)
        print(f"\n{Fore.GREEN}✓ Configuration saved successfully!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}✗ Configuration discarded.{Style.RESET_ALL}")
