import sys
import argparse
import app.core as core
import app.config as config
import app.utils as utils
import app.health as health
import app.setup as setup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically transcribe WhatsApp voice notes to your clipboard using OpenAI Whisper.",
    )

    group = parser.add_argument_group("Tools & Diagnostics")

    group.add_argument(
        "--health",
        action="store_true",
        help="Run system diagnostics to verify dependencies and folder access.",
    )
    group.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup to configure the application.",
    )
    group.add_argument(
        "--show-config",
        action="store_true",
        help="Shows the current configuration of the application.",
    )
    group.add_argument(
        "--logs",
        "-l",  # Short flag -l is handy
        dest="show_logs",
        action="store_true",
        help="Print the last 50 lines of the most recent transcription log file.",
    )
    group.add_argument(
        "--app-logs",
        action="store_true",
        help="Print the last 50 lines of the most recent app log file.",
    )

    # --- 1. CONFIGURATION CHECK ---
    args = parser.parse_args()

    is_configured = config.load_configuration()
    config.detect_whatsapp_path()

    if args.setup or not is_configured:
        setup.run_interactive_wizard()

        # Reload to ensure variables are updated
        if not config.load_configuration():
            sys.exit(1)

        # If the user ran --setup explicitly, we usually exit after saving
        if args.setup:
            return

    # --- 3. RUN HEALTH OR APP OR LOGS OR CONFIG ---
    if args.health:
        health.run_diagnostics()
        return

    if args.show_config:
        config.show_config()
        return

    if args.show_logs:
        utils.show_logs("transcribed_audio")
        return

    if args.app_logs:
        utils.show_logs("app")
        return

    core.run_transcriber()


if __name__ == "__main__":
    main()
