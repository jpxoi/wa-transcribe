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
* **Smart Maintenance:** Automatically cleans up AI models that haven't been used in 3 days (configurable) to save disk space.
* **Startup Backfill:** Scans for missed voice notes from the last hour upon launch to ensure nothing is lost.
* **📋 Auto-Clipboard & Logging:**
  * Text is copied to clipboard (`Cmd+V` / `Ctrl+V`).
  * Transcripts are saved to daily logs (e.g., `2026-01-27_daily.log`).

## 🚀 Prerequisites

### 1. Install FFmpeg

Whisper relies on FFmpeg for audio processing.

* **macOS:** `brew install ffmpeg`
* **Windows:** `choco install ffmpeg` (or download binaries from ffmpeg.org and add to PATH).

### 2. Python 3.10+

Ensure you have a modern Python version installed. You can download it from [python.org](https://www.python.org/downloads/).

## 🛠️ Installation

### Clone the repository

```bash
git clone https://github.com/jpxoi/wa-transcriber.git
cd wa-transcriber
```

### Install the package

This will install the package in your system's Python environment. You can also use a virtual environment if you prefer.

```bash
pip install .
```

### Run the Health Check (Crucial)

Before running the main program, run the included health check tool. This script analyzes your **System RAM** (CPU/MPS) or **VRAM** (NVIDIA) and calculates exactly which Whisper model your computer can handle safely.

```bash
wa-transcriber --health
```

* ✅ Verifies FFmpeg installation.
* ✅ Detects Hardware Acceleration (CUDA vs MPS vs CPU).
* ✅ Calculates memory overhead and suggests the best `MODEL_SIZE`.

## ⚙️ Configuration

Run the interactive setup wizard to configure the application:

```bash
wa-transcriber --setup
```

This will guide you through:

* **Model Selection:** choosing the appropriate Whisper model size.
* **Language:** setting a preferred language or using auto-detection.
* **WhatsApp Path:** automatically detecting or manually specifying the WhatsApp Media folder.
* **Hardware Limits:** configuring RAM and VRAM usage limits.

To view your current configuration at any time, run:

```bash
wa-transcriber --config
```

Configuration is stored in `config.json` in your system's application data directory (e.g., `~/Library/Application Support/wa-transcriber/` on macOS).

### Model Selection Reference

The setup wizard will suggest a model based on your hardware, but you can choose any of the following:

| Model | VRAM/RAM Req | Speed | Accuracy | Best For |
| --- | --- | --- | --- | --- |
| `tiny` | ~1 GB | ⚡️ Instant | Low | Older laptops |
| `base` | ~1 GB | 🚀 Very Fast | Decent | Quick snippets |
| `small` | ~2 GB | 🏃 Fast | Good | General usage |
| `medium` | ~5 GB | ⚖️ Balanced | Great | Professional use |
| `turbo` | ~6 GB | 🏎️ **Optimized** | **Excellent** | **M1/M2/M3 & RTX 3060+** |
| `large-v3` | ~10 GB | 🐌 Slow | Perfect | Heavy accents / Noisy audio |

### Advanced Settings

The following settings can be fine-tuned via the setup wizard or by manually editing `config.json`:

* **Scan Lookback:** Number of hours to check for missed files on startup.
* **Model Cleanup:** Automatically delete models unused for a set number of days.
* **Memory Limits:** Adjust how aggressively the script uses System RAM or GPU VRAM.

## 🏃 Usage

Run the main script. It will initialize the model and start watching the folder.

```bash
wa-transcriber

```

**Workflow:**

1. Script loads (shows a progress bar for model loading).
2. **Startup Scan:** Checks for missed files from the last hour.
3. "👀 Watching Folder" message appears.
4. Receive a voice note in WhatsApp Desktop.
5. **Instant Result:**

* Console shows: `⚡️ [WORKING] Processing: audio_file.opus`
* Then: `✅ [DONE] Transcript: Hello world...`
* Clipboard: Updated automatically.

## 🛠️ CLI Reference

| Command | Description |
| --- | --- |
| `wa-transcriber` | Starts the main transcription service. |
| `wa-transcriber --setup` | Runs the interactive configuration wizard. |
| `wa-transcriber --health` | Runs system diagnostics and hardware checks. |
| `wa-transcriber --config` | Displays the current configuration. |
| `wa-transcriber --reset` | Resets the application by removing all user data and configuration. |
| `wa-transcriber --ta-logs` | Shows the last 50 lines of transcribed audio logs. |
| `wa-transcriber --app-logs` | Shows the last 50 lines of application logs. |

## ❓ Troubleshooting

* **"Clipboard unavailable":** On Linux, you may need `xclip` or `xsel`. On Windows/Mac, this usually works out of the box.
* **"CUDA out of memory":** Run `wa-transcriber --health` and switch to a smaller model (e.g., from `large` to `medium`).
* **Script doesn't trigger:** Ensure "Media Auto-Download" is ON in WhatsApp settings, or manually click the download arrow on the voice note.

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

## 📄 License

© 2026 Jean Paul Fernandez. Licensed under **GPLv3**.
