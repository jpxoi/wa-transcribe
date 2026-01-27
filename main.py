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
import subprocess
import time
import datetime
import whisper
import pyperclip
import torch
import config
import queue
import threading
from typing import Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from colorama import init, Fore, Style
from tqdm import tqdm

init(autoreset=True)

# Type alias for the Whisper model object (which is dynamically loaded)
# We use 'Any' here because whisper.model.Whisper is not easily importable
# for type hinting without loading the library, but semantically it returns a model class.
WhisperModel = Any


def get_compute_device() -> str:
    """
    Smartly selects the best hardware accelerator available.

    Returns:
        str: "mps" (Mac), "cuda" (NVIDIA), or "cpu".
    """
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def cleanup_unused_models(current_model_name: str) -> None:
    """
    Deletes models from the cache ONLY if they haven't been used in 7 days.
    """
    cache_dir: str = os.path.expanduser("~/.cache/whisper")
    if not os.path.exists(cache_dir):
        return

    keep_filename: str = f"{current_model_name}.pt"
    retention_period = 7 * 24 * 60 * 60  # 7 days in seconds
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


def save_to_log(text: str, source_file: str) -> None:
    """
    Appends transcript to a daily log file.

    Args:
        text (str): The transcribed text content.
        source_file (str): The full path to the original audio file.
    """
    if not os.path.exists(config.LOG_FOLDER_PATH):
        os.makedirs(config.LOG_FOLDER_PATH)

    date_str: str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file: str = os.path.join(config.LOG_FOLDER_PATH, f"{date_str}-Transcripts.txt")
    timestamp: str = datetime.datetime.now().strftime("%H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] File: {os.path.basename(source_file)}\n")
            f.write(f"{text}\n")
            f.write("-" * 40 + "\n")
    except IOError as e:
        print(f"{Fore.RED}⚠️ Log Error: {e}")


def print_banner():
    subprocess.run("cls" if os.name == "nt" else "clear", shell=True)

    print(
        f"{Fore.GREEN}●{Style.RESET_ALL} {Style.BRIGHT}WhatsApp Auto-Transcriber{Style.RESET_ALL} {Style.DIM}v{config.VERSION}{Style.RESET_ALL}"
    )
    print(
        f"{Style.DIM}  © 2026 {config.DEVELOPER_NAME} (@{config.DEVELOPER_USERNAME}){Style.RESET_ALL}"
    )
    print(f"{Style.DIM}" + "─" * 50 + f"{Style.RESET_ALL}")


class TranscriptionWorker(threading.Thread):
    def __init__(self, model: WhisperModel, audio_queue: queue.Queue) -> None:
        super().__init__()
        self.model = model
        self.queue = audio_queue
        # Daemon means this thread dies when the main program exits
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

        # Wait for file readiness
        if not self.wait_for_file_ready(filename):
            print(
                f"{Fore.RED}❌ [TIMEOUT]{Style.RESET_ALL} File not ready: {file_base}"
            )
            return

        try:
            audio = whisper.load_audio(filename)
            duration_secs = len(audio) / whisper.audio.SAMPLE_RATE
            duration_fmt = f"{duration_secs:.1f}s"
        except Exception:
            duration_fmt = "Unknown duration"

        # Updated Print Statement with Timestamp and Duration
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(
            f"\n{Style.DIM}[{timestamp}]{Style.RESET_ALL} {Fore.CYAN}⚡️ [WORKING]{Style.RESET_ALL} Processing: {Style.BRIGHT}{file_base}{Style.RESET_ALL} {Style.DIM}({duration_fmt}){queue_msg}"
        )

        start_time = time.time()

        try:
            # Smart FP16 selection:
            # CUDA (NVIDIA) benefits from FP16.
            # MPS (Mac) and CPU usually require FP32 (fp16=False) to avoid issues.
            use_fp16 = False
            if hasattr(self.model, "device") and self.model.device.type == "cuda":
                use_fp16 = True

            # Transcribe
            result: dict = self.model.transcribe(filename, fp16=use_fp16)
            text: str = result["text"].strip()

            elapsed = time.time() - start_time

            # 4. Success Output
            print(
                f"{Fore.GREEN}✅ [DONE in {elapsed:.1f}s]{Style.RESET_ALL} Transcript:"
            )
            print(f"{Fore.WHITE}{Style.DIM}   {text}")

            # 5. Clipboard & Log
            try:
                pyperclip.copy(text)
                print(f"{Fore.BLUE}   📋 Copied to clipboard")
            except Exception:
                print(f"{Fore.YELLOW}   ⚠️ Clipboard unavailable")

            save_to_log(text, filename)

        except Exception as e:
            print(f"{Fore.RED}❌ [ERROR]{Style.RESET_ALL} {e}")

    def wait_for_file_ready(self, filepath: str, timeout: int = 10) -> bool:
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
                f"{Fore.MAGENTA}📥 [NEW]{Style.RESET_ALL} Detected: {os.path.basename(filename)}"
            )
            self.queue.put(filename)


def main() -> None:
    print_banner()

    # 1. Verify Paths
    if config.WHATSAPP_INTERNAL_PATH is None or not os.path.exists(
        config.WHATSAPP_INTERNAL_PATH
    ):
        print(
            f"{Fore.RED}❌ Error:{Style.RESET_ALL} Could not find WhatsApp Media folder."
        )
        print(f"   OS Detected: {config.CURRENT_OS}")
        print("   Please open 'config.py' and manually set WHATSAPP_INTERNAL_PATH.")
        return

    # 2. Cleanup old models
    cleanup_unused_models(config.MODEL_SIZE)

    # 3. Detect Device & Load Model
    device = get_compute_device()
    print("-" * 50)
    print(f"{Fore.CYAN}🚀 Initializing System{Style.RESET_ALL}")
    print(f"   Device: {Style.BRIGHT}{device.upper()}{Style.RESET_ALL}")
    print(f"   Model:  {Style.BRIGHT}{config.MODEL_SIZE}{Style.RESET_ALL}")

    model: WhisperModel
    try:
        # We wrap this purely to show we are busy, though tqdm won't actually "progress"
        # nicely during a single function call, it adds a nice timestamp.
        with tqdm(total=1, bar_format="{desc}", desc="   ⏳ Loading...") as pbar:
            model = whisper.load_model(config.MODEL_SIZE, device=device)
            pbar.update(1)
    except RuntimeError as e:
        print(f"{Fore.RED}⚠️ Failed to load on {device}: {e}")
        print("   Falling back to CPU...")
        model = whisper.load_model(config.MODEL_SIZE, device="cpu")

    print(f"{Fore.GREEN}✅ System Ready!{Style.RESET_ALL}")

    # 4. Start Watching
    audio_queue: queue.Queue = queue.Queue()
    worker = TranscriptionWorker(model, audio_queue)  # noqa: F841

    event_handler = InternalAudioHandler(audio_queue)
    observer = Observer()
    observer.schedule(event_handler, path=config.WHATSAPP_INTERNAL_PATH, recursive=True)

    print(f"\n{Fore.CYAN}👀 Watching Folder:{Style.RESET_ALL}")
    print(f"   {config.WHATSAPP_INTERNAL_PATH}")
    print("-" * 50)
    print("   Press Ctrl+C to stop the script.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print(f"\n{Fore.RED}🛑 Stopping Transcriber.{Style.RESET_ALL}")
    observer.join()


if __name__ == "__main__":
    main()
