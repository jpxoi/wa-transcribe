# 🎙️ WhatsApp Auto-Transcriber

A lightning-fast, privacy-focused tool that automatically transcribes incoming WhatsApp voice notes on **macOS** and **Windows**.

**Why?** WhatsApp's native transcription is often unavailable or slow. This tool provides a superior, **100% local** alternative that works instantly the moment a voice note is downloaded, leveraging your hardware (GPU/NPU) for maximum speed.

> [!IMPORTANT]
> **Desktop Only:** This tool requires the official **WhatsApp Desktop App** (Store Version). It monitors the internal file system for new `.opus` files.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenAI Whisper](https://img.shields.io/badge/AI-OpenAI%20Whisper-green?logo=openai&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?logo=apple&logoColor=black)
![License](https://img.shields.io/badge/License-GPLv3-blue?logo=gnu&logoColor=white)

## ✨ Features

* **⚡️ Hardware Accelerated:**
* **macOS:** Native Metal Performance Shaders (MPS) for M1/M2/M3/M4 chips.
* **Windows:** Native NVIDIA CUDA support for GeForce RTX cards.

* **📂 Intelligent Monitoring:** Uses a threaded `Watchdog` observer to detect voice notes instantly without locking your system.
* **🏥 System Health Check:** Includes a utility to analyze your RAM/VRAM and suggest the optimal AI model size to prevent crashes.
* **🧹 Smart Maintenance:** Automatically cleans up AI models that haven't been used in 7 days to save disk space.
* **📋 Auto-Clipboard & Logging:**
* Text is copied to clipboard (`Cmd+V` / `Ctrl+V`).
* Transcripts are saved to daily logs (e.g., `2026-01-27-Transcripts.txt`).

## 🚀 Prerequisites

### 1. Install FFmpeg

Whisper relies on FFmpeg for audio processing.

* **macOS:** `brew install ffmpeg`
* **Windows:** `choco install ffmpeg` (or download binaries from ffmpeg.org and add to PATH).

### 2. Python 3.10+

Ensure you have a modern Python version installed.

## 🛠️ Installation

1. **Clone the repository:**

```bash
git clone https://github.com/jpxoi/wa-transcribe.git
cd wa-transcribe
```

1. **Create a virtual environment:**

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

## 🏥 Running the Health Check (Crucial)

Before running the main program, run the included health check tool. This script analyzes your **System RAM** (CPU/MPS) or **VRAM** (NVIDIA) and calculates exactly which Whisper model your computer can handle safely.

```bash
python check_health.py
```

* ✅ Verifies FFmpeg installation.
* ✅ Detects Hardware Acceleration (CUDA vs MPS vs CPU).
* ✅ Calculates memory overhead and suggests the best `MODEL_SIZE`.

## ⚙️ Configuration (`config.py`)

Open `config.py` to adjust settings.

### Model Selection

Based on the output of `check_health.py`, set your `MODEL_SIZE`:

| Model | VRAM/RAM Req | Speed | Accuracy | Best For |
| --- | --- | --- | --- | --- |
| `tiny` | ~1 GB | ⚡️ Instant | Low | Older laptops |
| `base` | ~1 GB | 🚀 Very Fast | Decent | Quick snippets |
| `small` | ~2 GB | 🏃 Fast | Good | General usage |
| `medium` | ~5 GB | ⚖️ Balanced | Great | Professional use |
| `turbo` | ~6 GB | 🏎️ **Optimized** | **Excellent** | **M1/M2/M3 & RTX 3060+** |
| `large-v3` | ~10 GB | 🐌 Slow | Perfect | Heavy accents / Noisy audio |

### WhatsApp Path

The script attempts to auto-detect paths on macOS.

* **Windows Users:** You likely need to set `MANUAL_PATH_OVERRIDE` in `config.py` to point to your WhatsApp Media folder (usually inside `AppData\Local\Packages`).

## 🏃 Usage

Run the main script. It will initialize the model and start watching the folder.

```bash
python main.py

```

**Workflow:**

1. Script loads (shows a progress bar for model loading).
2. "👀 Watching Folder" message appears.
3. Receive a voice note in WhatsApp Desktop.
4. **Instant Result:**

* Console shows: `⚡️ [WORKING] Processing: audio_file.opus`
* Then: `✅ [DONE] Transcript: Hello world...`
* Clipboard: Updated automatically.

## ❓ Troubleshooting

* **"Clipboard unavailable":** On Linux, you may need `xclip` or `xsel`. On Windows/Mac, this usually works out of the box.
* **"CUDA out of memory":** Run `python check_health.py` and switch to a smaller model (e.g., from `large` to `medium`).
* **Script doesn't trigger:** Ensure "Media Auto-Download" is ON in WhatsApp settings, or manually click the download arrow on the voice note.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

## 📄 License

© 2026 Jean Paul Fernandez. Licensed under **GPLv3**.
