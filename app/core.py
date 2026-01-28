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
import argparse
import queue
import threading
import app.config as config
import app.utils as utils
import app.health as health
from typing import Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from colorama import init, Fore, Style
from tqdm import tqdm

init(autoreset=True)

WhisperModel = Any


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


def save_to_log(text: str, source_file: str, duration: str, elapsed: float) -> None:
    """
    Appends transcript to a daily log file.

    Args:
        text (str): The transcribed text content.
        source_file (str): The full path to the original audio file.
    """
    os.makedirs(config.LOG_FOLDER_PATH, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(config.LOG_FOLDER_PATH, f"{date_str}_daily.log")

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


def get_processed_history(
    days_to_check: int = config.SCAN_LOG_HISTORY_DAYS,
) -> set[str]:
    """
    Scans existing logs to find filenames that are already processed.

    """
    processed_files = set()
    log_dir = config.LOG_FOLDER_PATH

    if not os.path.exists(log_dir):
        return processed_files

    today = datetime.date.today()
    dates_to_check = [today - datetime.timedelta(days=i) for i in range(days_to_check)]

    for date_obj in dates_to_check:
        log_filename = f"{date_obj.strftime('%Y-%m-%d')}_daily.log"
        log_path = os.path.join(log_dir, log_filename)

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "|" in line and "⏳" in line:
                            parts = line.split("|")
                            if len(parts) > 0:
                                filename = parts[0].replace("●", "").strip()
                                processed_files.add(filename)
            except Exception:
                continue

    return processed_files


def queue_recent_files(audio_queue: queue.Queue) -> None:
    """
    Recursively scans the folder and subfolders for recent audio files
    (based on config limit) that are NOT in the processed history.
    """
    history = get_processed_history()
    target_dir = config.WHATSAPP_INTERNAL_PATH

    lookback_hours = config.SCAN_LOOKBACK_HOURS

    if not os.path.exists(target_dir or not config.SCAN_LOOKBACK_ENABLED):
        return

    print(
        f"{Fore.CYAN}🔍 Startup Scan:{Style.RESET_ALL} Checking for missed files (last {lookback_hours}h)..."
    )

    now = time.time()
    cutoff = now - (lookback_hours * 3600)
    count = 0
    audio_files = []

    for root, _, files in os.walk(target_dir):
        for filename in files:
            if filename.endswith((".opus", ".m4a", ".mp3", ".wav")):
                filepath = os.path.join(root, filename)
                try:
                    # Get modification time
                    mtime = os.path.getmtime(filepath)

                    if mtime > cutoff:
                        audio_files.append((mtime, filepath, filename))
                except OSError:
                    continue

    audio_files.sort(key=lambda x: x[0])

    for _, filepath, filename in audio_files:
        if filename not in history:
            print(
                f"   {Fore.MAGENTA}+ Queuing missed file:{Style.RESET_ALL} {filename}"
            )
            audio_queue.put(filepath)
            count += 1

    if count == 0:
        print(f"   {Fore.GREEN}✓ All caught up.{Style.RESET_ALL}")
    else:
        print(f"   {Fore.GREEN}✓ Added {count} missed files to queue.{Style.RESET_ALL}")
    print("─" * 50)


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
            # MPS (Mac) and CPU usually require FP32 (fp16=False) to avoid issues.
            use_fp16 = False
            if hasattr(self.model, "device") and self.model.device.type == "cuda":
                use_fp16 = True

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
                print(f"{Fore.YELLOW}   ! Clipboard unavailable")

            save_to_log(text, filename, duration_fmt, elapsed)

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


def run_transcriber() -> None:
    utils.print_banner()

    # 1. Verify Paths
    if config.WHATSAPP_INTERNAL_PATH is None or not os.path.exists(
        config.WHATSAPP_INTERNAL_PATH
    ):
        print(
            f"{Fore.RED}✗ [ERROR] Could not find WhatsApp Media folder.{Style.RESET_ALL}"
        )
        print(f"   OS Detected: {config.CURRENT_OS}")
        print("   Please open 'app/config.py' and manually set WHATSAPP_INTERNAL_PATH.")
        return

    # 2. Cleanup old models (if enabled)
    if config.MODEL_CLEANUP_ENABLED:
        cleanup_unused_models(config.MODEL_SIZE)

    # 3. Detect Device & Load Model
    device = utils.get_compute_device()
    print("─" * 50)
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
        print(f"{Fore.RED}✗ Failed to load on {device}: {e}")
        print("   Falling back to CPU...")
        model = whisper.load_model(config.MODEL_SIZE, device="cpu")

    print(f"{Fore.GREEN}✓ System Ready!{Style.RESET_ALL}")

    # 4. Initialize Transcription Worker
    audio_queue: queue.Queue = queue.Queue()
    worker = TranscriptionWorker(model, audio_queue)  # noqa: F841

    # 5. Queue recent files (if enabled)
    if config.SCAN_LOOKBACK_ENABLED:
        queue_recent_files(audio_queue)

    # 6. Start Watching
    event_handler = InternalAudioHandler(audio_queue)
    observer = Observer()
    observer.schedule(event_handler, path=config.WHATSAPP_INTERNAL_PATH, recursive=True)

    print(f"\n{Fore.CYAN}👀 Watching Folder:{Style.RESET_ALL}")
    print(f"   {config.WHATSAPP_INTERNAL_PATH}")
    print("─" * 50)
    print("   Press Ctrl+C to stop the script.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print(f"\n{Fore.RED}● Stopping Transcriber.{Style.RESET_ALL}")
    observer.join()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically transcribe WhatsApp voice notes to your clipboard using OpenAI Whisper.",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run system diagnostics to verify dependencies and folder access.",
    )

    args = parser.parse_args()

    if args.health:
        health.run_diagnostics()
        return

    run_transcriber()


if __name__ == "__main__":
    main()
