# 🎙️ WhatsApp Auto-Transcriber

A lightning-fast, privacy-focused tool that automatically transcribes incoming WhatsApp voice notes on macOS and Windows using OpenAI's Whisper model.

**Why?** WhatsApp's native transcription is often slow, inaccurate, or simply unavailable in many regions. This tool provides a superior, 100% local alternative that works instantly the moment a voice note is downloaded.

> [!IMPORTANT]
> **Desktop Only:** This tool requires the official **WhatsApp Desktop App** (Mac App Store or Windows Store version). It **does not work** with WhatsApp Web because the web version does not store audio files locally.

**Optimized for Apple Silicon (M1/M2/M3/M4)** to run natively on the GPU/NPU, keeping your CPU cool and battery life high.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![OpenAI Whisper](https://img.shields.io/badge/AI-OpenAI%20Whisper-green?logo=openai&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?logo=apple&logoColor=black)
![License](https://img.shields.io/badge/License-GPLv3-blue?logo=gnu&logoColor=white)

## ✨ Features

* **⚡️ Instant Transcription:** Detects new `.opus` audio files the moment WhatsApp downloads them to your disk.
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

1. Download from [ffmpeg.org](https://ffmpeg.org/download.html).
2. Add the `bin` folder to your System PATH.

### 2. Python 3.10+

Ensure you have a modern version of Python installed. Check with `python --version`.

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/jpxoi/wa-transcribe.git
cd wa-transcribe
```

### 2. Create a virtual environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

The project is ready to run out of the box, but you can customize settings in `config.py`.

### 🧠 Model Selection (`MODEL_SIZE`)

Choose the balance between speed and accuracy:

| Model | Speed | Accuracy | Memory | Best For |
| --- | --- | --- | --- | --- |
| `tiny` | ⚡️ Fastest | Low | ~1GB | Older Intel Macs |
| `base` | 🚀 Fast | Decent | ~1GB | Quick summaries |
| `medium` | ⚖️ **Default** | **Excellent** | ~5GB | **Apple Silicon (M1/M2/M3)** |
| `large-v3` | 🐌 Slowest | Perfect | ~10GB | Complex accents/noisy audio |
| `turbo` | 🏎️ Ultra Fast | Very Good | ~6GB | Real-time needs |

### 📂 Folder Path (`WHATSAPP_INTERNAL_PATH`)

The script supports auto-detection of the WhatsApp Media folder on **macOS**. If you are on **Windows**, or if auto-detection fails, you must manually set your path in `config.py` using the `MANUAL_PATH_OVERRIDE` variable.

## 🏃 Usage

Simply run the script. It will run in the background and watch for new files.

```bash
python main.py
```

**What happens next?**

1. Open **WhatsApp Desktop** on your computer.
2. Receive a voice note (it must be downloaded/played once to save to disk).
3. The script detects the new `.opus` file.
4. **Done!** The text is copied to your clipboard and saved to the `transcribed_audio_logs/` folder.

> [!WARNING]  
> This tool watches your internal WhatsApp media folder. It effectively transcribes **every** voice note downloaded to your computer, including those from muted group chats, if WhatsApp auto-downloads them.

## ❓ Troubleshooting

### "The script runs but nothing happens when I get a voice note."

* Ensure you are using the **Desktop App**, not the Web browser version.
* Make sure "Media Auto-Download" is enabled in WhatsApp Settings, or click the download icon on the voice note to ensure the file is saved to disk.

### "FileNotFoundError / Path not found"

* WhatsApp changes folder paths occasionally.
* Open `config.py` and set your path manually in `MANUAL_PATH_OVERRIDE`.
* *Tip for Mac users:* The path is usually `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media`.

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.
See the `LICENSE` file for details.
