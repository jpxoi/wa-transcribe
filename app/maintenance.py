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
import time
from app import config
from colorama import Fore, Style


def cleanup_unused_models(
    current_model_name: str, retention_days: int = config.MODEL_RETENTION_DAYS
) -> None:
    """
    Deletes models from the cache ONLY if they haven't been used in 7 days.
    """
    cache_dir: str = os.path.expanduser("~/.cache/whisper")
    if not os.path.exists(cache_dir):
        return

    keep_filename: str = f"{current_model_name}.pt"
    retention_period = retention_days * 24 * 60 * 60  # in seconds
    current_time = time.time()

    print(
        f"{Fore.CYAN}🧹 Maintenance:{Style.RESET_ALL} Checking for old, unused models..."
    )

    for filename in os.listdir(cache_dir):
        if filename in config.KNOWN_MODELS and filename != keep_filename:
            file_path = os.path.join(cache_dir, filename)
            try:
                last_access = os.stat(file_path).st_atime

                if (current_time - last_access) > retention_period:
                    os.remove(file_path)
                    print(
                        f"   {Fore.YELLOW}🗑️ Deleted old model:{Style.RESET_ALL} {filename}"
                    )
                else:
                    pass
            except OSError:
                pass
