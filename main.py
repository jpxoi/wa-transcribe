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
import torch
import config
import queue
import threading
from typing import Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# Type alias for the Whisper model object (which is dynamically loaded)
# We use 'Any' here because whisper.model.Whisper is not easily importable
# for type hinting without loading the library, but semantically it returns a model class.
WhisperModel = Any


def get_compute_device() -> str:
    """
    Smartly selects the best hardware accelerator available.
    Returns: "mps" (Mac), "cuda" (NVIDIA), or "cpu".
    """
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def cleanup_unused_models(current_model_name: str) -> None:
    """
    Deletes unused Whisper models from the cache to save disk space.

    Args:
        current_model_name: The name of the model currently in use (e.g., "medium")
    """
    cache_dir: str = os.path.expanduser("~/.cache/whisper")
    if not os.path.exists(cache_dir):
        return

    keep_filename: str = f"{current_model_name}.pt"
    print("🧹 Maintenance: Checking for unused models...")

    for filename in os.listdir(cache_dir):
        if filename in config.KNOWN_MODELS and filename != keep_filename:
            try:
                file_path: str = os.path.join(cache_dir, filename)
                os.remove(file_path)
                print(f"   🗑️ Deleted unused model: {filename}")
            except OSError:
                # Silently fail on permission errors to avoid spamming user
                pass


def save_to_log(text: str, source_file: str) -> None:
    """
    Appends transcript to a daily log file.

    Args:
        text: The transcribed text content.
        source_file: The full path to the original audio file.
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
        print(f"⚠️ Could not save log: {e}")


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
        print(f"\n⚡️ Processing: {os.path.basename(filename)}")

        # Robust file readiness check
        # Waits until file size is stable (file write is complete)
        if not self.wait_for_file_ready(filename):
            print(f"⚠️ Timeout waiting for file: {filename}")
            return

        try:
            # FIX: fp16=False is crucial for M-series chips to avoid NaN errors
            result: dict = self.model.transcribe(filename, fp16=False)
            text: str = result["text"].strip()

            print(f"✅ Transcript: {text}")

            # Copy to Clipboard
            pyperclip.copy(text)

            # Save to Log
            save_to_log(text, filename)

        except Exception as e:
            print(f"❌ Error processing file: {e}")

    def wait_for_file_ready(self, filepath: str, timeout: int = 10) -> bool:
        """
        Polls the file size to ensure it has finished writing.
        Returns True if stable, False if timeout.
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(filepath)
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

            print(f"📥 Queued: {os.path.basename(filename)}")
            self.queue.put(filename)


def main() -> None:
    # 1. Verify Paths
    if config.WHATSAPP_INTERNAL_PATH is None or not os.path.exists(
        config.WHATSAPP_INTERNAL_PATH
    ):
        print("❌ Error: Could not find WhatsApp Media folder.")
        print(f"   OS Detected: {config.CURRENT_OS}")
        print("   Please open 'config.py' and manually set WHATSAPP_INTERNAL_PATH.")
        return

    # 2. Cleanup old models
    cleanup_unused_models(config.MODEL_SIZE)

    # 3. Detect Device & Load Model
    device: str = get_compute_device()
    print(f"🚀 Loading Whisper Model ({config.MODEL_SIZE}) on {device.upper()}...")

    model: WhisperModel
    try:
        model = whisper.load_model(config.MODEL_SIZE, device=device)
    except RuntimeError as e:
        print(f"⚠️ Failed to load on {device}: {e}")
        print("   Falling back to CPU...")
        model = whisper.load_model(config.MODEL_SIZE, device="cpu")

    # 4. Start Watching
    audio_queue: queue.Queue = queue.Queue()

    # Start the worker thread
    worker = TranscriptionWorker(model, audio_queue)  # noqa: F841

    event_handler = InternalAudioHandler(audio_queue)
    observer = Observer()

    # We ignore the type error here because Observer.schedule expects a specific path type
    # but our config guarantees a string path if the check passes.
    observer.schedule(event_handler, path=config.WHATSAPP_INTERNAL_PATH, recursive=True)

    print(f"\n👀 Watching: {config.WHATSAPP_INTERNAL_PATH}")
    print(f"📝 Logs: {config.LOG_FOLDER_PATH}")
    print("---------------------------------------------------")
    print("   Press Ctrl+C to stop the script.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Stopping Transcriber.")
    observer.join()


if __name__ == "__main__":
    main()
