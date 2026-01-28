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
import datetime
import whisper
import pyperclip
import queue
import threading
from typing import Any
from app import db, config
from colorama import init, Fore, Style

init(autoreset=True)


WhisperModel = Any


def save_to_log(text: str, source_file: str, duration: str, elapsed: float) -> None:
    """
    Appends transcript to a daily log file.

    Args:
        text (str): The transcribed text content.
        source_file (str): The full path to the original audio file.
    """
    os.makedirs(config.TRANSCRIBED_AUDIO_LOGS_DIR, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(config.TRANSCRIBED_AUDIO_LOGS_DIR, f"{date_str}_daily.log")

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    filename = os.path.basename(source_file)

    header_line = f"─── {timestamp} INFO ".ljust(80, "─")

    meta_info = f"{filename}  |  ⏳ {duration}  |  ⏱ done in {elapsed:.1f}s"

    log_entry = f"{header_line}\n{meta_info}\n\n{text.strip()}\n\n"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except IOError:
        pass


class TranscriptionWorker(threading.Thread):
    def __init__(self, model: WhisperModel, audio_queue: queue.Queue) -> None:
        super().__init__()
        self.model = model
        self.queue = audio_queue
        self.daemon = True
        self.start()

    def run(self) -> None:
        while True:
            filename: str = self.queue.get()
            try:
                self.process_file(filename)
            finally:
                self.queue.task_done()

    def process_file(self, filename: str) -> None:
        """
        Processes a single audio file and copies the transcript to the clipboard.

        Args:
            filename (str): The path to the audio file to process.
        """
        file_base = os.path.basename(filename)
        pending_count = self.queue.qsize()
        queue_msg = f" ({pending_count} more in queue)" if pending_count > 0 else ""

        if not self.wait_for_file_ready(filename):
            print(f"{Fore.RED}✗ [TIMEOUT]{Style.RESET_ALL} File not ready: {file_base}")
            return

        try:
            audio = whisper.load_audio(filename)
            duration_secs = len(audio) / whisper.audio.SAMPLE_RATE

            m, s = divmod(duration_secs, 60)

            if m > 0:
                duration_fmt = f"{int(m)}m {int(s)}s"
            else:
                duration_fmt = f"{s:.1f}s"

        except Exception:
            duration_fmt = "Unknown duration"

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(
            f"\n{Style.DIM}[{timestamp}]{Style.RESET_ALL} {Fore.CYAN}⚡️ [WORKING]{Style.RESET_ALL} Processing: {Style.BRIGHT}{file_base}{Style.RESET_ALL} {Style.DIM}({duration_fmt}){queue_msg}"
        )

        start_time = time.time()

        try:
            # Smart FP16 selection:
            # CUDA (NVIDIA) benefits from FP16.
            # MPS (Mac) can use FP16 if explicitly enabled (requires recent PyTorch/OS).
            # CPU always uses FP32 (fp16=False) to avoid warnings/crashes.

            use_fp16 = False
            device_type = "cpu"  # Default to CPU

            if hasattr(self.model, "device"):
                device_type = self.model.device.type  # Get actual device type

            if device_type == "cuda":
                use_fp16 = True
            elif device_type == "mps":
                use_fp16 = getattr(config, "ENABLE_MPS_FP16", False)

            # Transcribe
            result: dict = self.model.transcribe(
                filename, fp16=use_fp16, language=config.TRANSCRIPTION_LANGUAGE
            )
            text: str = result["text"].strip()

            elapsed = time.time() - start_time

            # 4. Success Output
            print(
                f"{Fore.GREEN}✓ [DONE in {elapsed:.1f}s]{Style.RESET_ALL} Transcript:"
            )
            print(f"{Fore.WHITE}{Style.DIM}   {text}")

            # 5. Clipboard & Log
            try:
                pyperclip.copy(text)
                print(f"{Fore.BLUE}   📋 Copied to clipboard")
            except Exception:
                print(f"{Fore.YELLOW}   ⚠ Clipboard unavailable")

            save_to_log(text, filename, duration_fmt, elapsed)
            db.add_processed_file(file_base, filename)

        except Exception as e:
            print(f"{Fore.RED}✗ [ERROR]{Style.RESET_ALL} {e}")

    def wait_for_file_ready(
        self, filepath: str, timeout: int = config.FILE_READY_TIMEOUT
    ) -> bool:
        """
        Polls the file size to ensure it has finished writing.

        Args:
            filepath (str): The path to the file to check.
            timeout (int): The maximum time to wait for the file to be ready.

        Returns:
            bool: True if the file is ready, False if the timeout is reached.
        """
        start_time: float = time.time()
        last_size: int = -1

        while time.time() - start_time < timeout:
            try:
                current_size: int = os.path.getsize(filepath)
                if current_size == last_size and current_size > 0:
                    return True
                last_size = current_size
                time.sleep(0.5)
            except OSError:
                time.sleep(0.5)

        return False
