# 🎙️ WhatsApp Auto-Transcriber

A lightning-fast, privacy-focused tool that automatically transcribes incoming WhatsApp voice notes on macOS (and Windows) using OpenAI's Whisper model.

**Optimized for Apple Silicon (M1/M2/M3/M4)** to run purely on the GPU/NPU, keeping your CPU cool and battery life high.

## ✨ Features

* **⚡️ Instant Transcription:** Detects new `.opus` audio files the moment WhatsApp downloads them.
* **📋 Auto-Clipboard:** The transcribed text is automatically copied to your clipboard. Just hit `Cmd+V`.
* **🔒 Privacy First:** Runs 100% locally on your machine. No audio is ever sent to the cloud.
* **🍎 Apple Silicon Native:** Uses Metal Performance Shaders (MPS) to accelerate inference on Mac GPUs.
* **💾 Smart Storage:** Automatically creates daily text logs of all voice notes and cleans up unused AI models to save disk space.
* **💻 Cross-Platform:** Auto-detects your OS to find the correct WhatsApp media folder.

## 🚀 Prerequisites

### 1. Install FFmpeg

Whisper requires FFmpeg to process audio files.

**macOS:**

```bash
brew install ffmpeg

```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your System PATH.

### 2. Python 3.10+

Ensure you have a modern version of Python installed.

## 🛠️ Installation

1. **Clone the repository:**

```bash
git clone https://github.com/jpxoi/wa-transcriber.git
cd wa-transcriber
```

1. **Create a virtual environment (Recommended):**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```

1. **Install dependencies:**

```bash
pip install -r requirements.txt

```

## ⚙️ Configuration

The project is ready to run out of the box, but you can customize it in `config.py`.

* **`MODEL_SIZE`**:
* `tiny`: Less accurate, but faster and uses less memory.
* `base` / `small`: Fast, low memory usage.
* `medium` **(Default)**: The sweet spot. Excellent accuracy, runs fast on M1/M2/M3 chips.
* `large-v3`: Best possible accuracy. Slower, requires ~4GB VRAM.
* `turbo`: New high-speed model (8x real-time).

* **`WHATSAPP_INTERNAL_PATH`**:
* The script attempts to auto-detect your WhatsApp Media folder.
* If it fails, you can manually paste your path here.

## 🏃 usage

Simply run the script. It will run in the background and watch for new files.

```bash
python main.py

```

**What happens next?**

1. Open WhatsApp on your computer.
2. When you receive a voice note, the script detects the file creation.
3. It transcribes the audio.
4. **Done!** The text is now in your clipboard and saved to `transcribed_audio_logs/`.

> **Note:** Because this script reads internal WhatsApp files, it may transcribe *every* incoming voice note (including those from muted groups) if they are downloaded to your disk.

## 🧠 How it Works

1. **Watchdog:** Monitors the file system for specific audio extensions (`.opus`, `.m4a`).
2. **Debounce:** Prevents double-processing if the OS "touches" the file multiple times during download.
3. **Whisper (MPS):** Loads the AI model onto the Mac GPU (Metal) or NVIDIA GPU (CUDA) for rapid inference.
4. **Pyperclip:** Injects the result into the system clipboard.

## 📂 Folder Structure

```text
wa-transcriber/
├── config.py           # Settings & Path Detection
├── main.py             # Core logic & Watchdog
├── requirements.txt    # Dependencies
└── transcribed_audio_logs/  # (Auto-generated) Daily logs
    ├── 2024-05-20-Transcripts.txt
    └── ...
```

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
