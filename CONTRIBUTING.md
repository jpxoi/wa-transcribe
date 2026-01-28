# Contributing to WhatsApp Auto-Transcriber

First off, thank you for considering contributing to this project! It's people like you that make open-source software such a powerful tool.

Whether you're fixing a bug, improving the documentation, or adding a new feature (like support for Linux or new audio formats), your help is welcome.

## 📋 Table of Contents

1. [Code of Conduct](https://www.google.com/search?q=%23code-of-conduct)
2. [How to Contribute](https://www.google.com/search?q=%23how-to-contribute)

* [Reporting Bugs](https://www.google.com/search?q=%23reporting-bugs)
* [Suggesting Enhancements](https://www.google.com/search?q=%23suggesting-enhancements)

1. [Development Guide](https://www.google.com/search?q=%23development-guide)

* [Setting Up the Environment](https://www.google.com/search?q=%23setting-up-the-environment)
* [Project Structure](https://www.google.com/search?q=%23project-structure)

1. [Coding Standards](https://www.google.com/search?q=%23coding-standards)
2. [Submitting a Pull Request](https://www.google.com/search?q=%23submitting-a-pull-request)

## 🤝 Code of Conduct

This project is open to everyone. Please be respectful, empathetic, and patient. We are all here to learn and build cool things together.

## 🚀 How to Contribute

### Reporting Bugs

Before creating a bug report, please check the following:

1. **Run the Health Check:** Run `wa-transcriber health` and see if it flags any missing dependencies or hardware issues.
2. **Search Issues:** Check if the issue has already been reported.

If you are opening a new issue, please include:

* **OS:** (e.g., macOS Sequoia 15.1, Windows 11)
* **Hardware:** (e.g., Apple M2 Pro, NVIDIA RTX 3060)
* **Log Output:** The error message from the terminal.
* **WhatsApp Version:** Desktop App or Store Version?

### Suggesting Enhancements

Have an idea to make the tool faster or smarter?

* Open an issue with the tag **enhancement**.
* Explain **why** this feature would be useful.
* If possible, describe **how** you would implement it (e.g., "Use `pyannote` for speaker diarization").

## 💻 Development Guide

### Setting Up the Environment

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:

```bash
git clone https://github.com/YOUR-USERNAME/wa-transcriber.git
cd wa-transcriber
```

1. **Create a Virtual Environment:**

This project uses Python 3.14 and was developed using the `uv` package manager. However, it is compatible with native Python virtual environments.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

1. **Install Dependencies:**

```bash
pip install -r requirements.txt
```

### Project Structure

The project is structured as follows:

* `app/`: Contains the main application code.
* `app/cli.py`: The main entry point and argument parser.
* `app/config.py`: Handles configuration storage (`config.json`) and defaults.
* `app/core.py`: Core application logic, including the `Watchdog` observer and proper threading.
* `app/db.py`: Database management for tracking processed files (SQLite).
* `app/health.py`: Diagnostic tool for memory, hardware, and dependency analysis.
* `app/setup.py`: Interactive setup wizard for initializing configuration.
* `app/utils.py`: Utility functions for UI banners, device detection, and platform specifics.

## 📏 Coding Standards

To maintain the quality and stability of the project, please adhere to these standards:

### 1. Type Hinting is Mandatory

We use Python's `typing` module to ensure code clarity.

* **Bad:** `def process(file):`
* **Good:** `def process(file: str) -> None:`

### 2. Cross-Platform Compatibility

This tool runs on both **macOS** and **Windows**.

* Avoid hardcoded paths like `/Users/name/`. Use `os.path.join()` or `os.path.expanduser("~")`.
* If using OS-specific commands (like `cls` vs `clear`), use the wrappers provided in `helpers.py`.

### 3. Thread Safety

The transcription process runs in a daemon thread (`TranscriptionWorker`). If you modify shared resources (like the log file or console output), ensure you aren't causing race conditions.

### 4. UI & Logging

* Use `colorama` for terminal output.
* Success messages: `Fore.GREEN`
* Warnings/Working: `Fore.YELLOW` or `Fore.CYAN`
* Errors: `Fore.RED`

### 5. License Headers

Please ensure any new files include the GPLv3 copyright header found in existing files.

## 📥 Submitting a Pull Request

1. Create a new branch for your feature:

```bash
git checkout -b feature/amazing-new-feature
```

1. Make your changes.
2. **Test your changes:**

* Run `wa-transcriber health` to ensure logic holds up.
* Simulate a file drop to ensure the watcher triggers.

1. Commit your changes with a clear message:

* `feat: added speaker identification`
* `fix: resolved path issue on Windows 10`

1. Push to your fork and open a Pull Request.

### A Note on Configuration

You should use `wa-transcriber setup` to configure the application for your local machine (this creates a `config.json`). **Please do not commit local changes to `config.json`** (such as path overrides) unless you are changing the project defaults.

**Happy Coding!** 🎧✨
