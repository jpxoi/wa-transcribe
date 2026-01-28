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
import whisper
import queue
from typing import Any
from watchdog.observers import Observer
from colorama import init, Fore, Style
from tqdm import tqdm
from app import db, utils, config, maintenance
from app.monitor import InternalAudioHandler
from app.transcriber import TranscriptionWorker

init(autoreset=True)

WhisperModel = Any


def queue_recent_files(audio_queue: queue.Queue) -> None:
    """
    Recursively scans the folder and subfolders for recent audio files
    (based on config limit) that are NOT in the processed history.

    Args:
        audio_queue (queue.Queue): The queue to add the files to.
    """
    target_dir = config.WHATSAPP_INTERNAL_PATH
    lookback_hours = config.SCAN_LOOKBACK_HOURS

    if not os.path.exists(target_dir or not config.SCAN_LOOKBACK_ENABLED):
        return

    print(
        f"\n{Fore.CYAN}🔍 Startup Scan:{Style.RESET_ALL} Checking for missed files (last {lookback_hours}h)..."
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
                    mtime = os.path.getmtime(filepath)
                    if mtime > cutoff:
                        audio_files.append((mtime, filepath, filename))
                except OSError:
                    continue

    audio_files.sort(key=lambda x: x[0])

    # Check DB and queue if new
    for _, filepath, filename in audio_files:
        if not db.is_file_processed(filename):
            print(
                f"   {Fore.MAGENTA}+ Queuing missed file:{Style.RESET_ALL} {filename}"
            )
            audio_queue.put(filepath)
            count += 1

    if count == 0:
        print(f"   {Fore.GREEN}✓ All caught up.{Style.RESET_ALL}")
    else:
        print(f"   {Fore.GREEN}✓ Added {count} missed files to queue.{Style.RESET_ALL}")


def run_transcriber() -> None:
    utils.print_banner()

    # 0. Initialize Database
    db.init_db()
    db.migrate_from_logs()

    # 1. Verify Paths
    if config.WHATSAPP_INTERNAL_PATH is None or not os.path.exists(
        config.WHATSAPP_INTERNAL_PATH
    ):
        print(
            f"{Fore.RED}✗ [ERROR] Could not find WhatsApp Media folder.{Style.RESET_ALL}"
        )
        print(f"   OS Detected: {config.SYSTEM}")
        print("   Please run 'wa-transcriber setup' to configure the path.")
        return

    # 2. Cleanup old models (if enabled)
    if config.MODEL_CLEANUP_ENABLED:
        maintenance.cleanup_unused_models(config.MODEL_SIZE)

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

    print(
        f"\n{Fore.CYAN}📂 Logs saved to:{Style.RESET_ALL} {Style.DIM}{os.path.abspath(config.TRANSCRIBED_AUDIO_LOGS_DIR)}{Style.RESET_ALL}"
    )

    print(f"\n{Fore.CYAN}👀 Watching Folder:{Style.RESET_ALL}")
    print(
        f"   {Style.DIM}{os.path.abspath(config.WHATSAPP_INTERNAL_PATH)}{Style.RESET_ALL}"
    )
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


def show_logs() -> None:
    """Show logs."""
    print(
        f"\n{Fore.CYAN}📂 Logs saved to:{Style.RESET_ALL} {Style.DIM}{os.path.abspath(config.TRANSCRIBED_AUDIO_LOGS_DIR)}{Style.RESET_ALL}"
    )
