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
import queue
from typing import Optional
from colorama import Fore, Style
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class InternalAudioHandler(FileSystemEventHandler):
    def __init__(self, audio_queue: queue.Queue) -> None:
        self.queue: queue.Queue = audio_queue
        self.last_transcribed: Optional[str] = None

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Triggered when a file is created in the watched directory.

        Args:
            event (FileSystemEvent): The file system event.
        """
        if event.is_directory:
            return

        # src_path is strictly a string in this context
        filename: str = str(event.src_path)

        # Watch for common audio extensions
        if filename.endswith((".opus", ".m4a", ".mp3", ".wav")):
            # Debounce duplicate events
            if self.last_transcribed == filename:
                return
            self.last_transcribed = filename

            print(
                f"\n{Fore.MAGENTA}📥 [NEW]{Style.RESET_ALL} Detected: {os.path.basename(filename)}"
            )
            self.queue.put(filename)
