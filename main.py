import os
import time
import datetime
import whisper
import pyperclip
import torch
import config
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


class InternalAudioHandler(FileSystemEventHandler):
    def __init__(self, model: WhisperModel) -> None:
        self.model: WhisperModel = model
        self.last_transcribed: Optional[str] = None

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Triggered when a file is created in the watched directory.
        """
        if event.is_directory:
            return

        # src_path is strictly a string in this context, but type hint suggests Union[str, bytes]
        filename: str = str(event.src_path)

        # Watch for common audio extensions
        if filename.endswith((".opus", ".m4a", ".mp3", ".wav")):
            # Debounce duplicate events
            if self.last_transcribed == filename:
                return
            self.last_transcribed = filename

            print(f"\n⚡️ New Audio Detected: {os.path.basename(filename)}")

            try:
                # Wait for file write to complete (network latency/disk IO)
                time.sleep(1.0)

                # Transcribe
                # The transcribe method returns a Dictionary with keys like "text", "segments", etc.
                result: dict = self.model.transcribe(filename)
                text: str = result["text"].strip()  # type: ignore

                print(f"✅ Transcript: {text}")

                # Copy to Clipboard
                pyperclip.copy(text)

                # Save to Log
                save_to_log(text, filename)

            except Exception as e:
                print(f"❌ Error processing file: {e}")


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
    event_handler = InternalAudioHandler(model)
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
