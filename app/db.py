import sqlite3
import os
import datetime
import logging
import re
import app.config as config
from typing import Set, Generator
from contextlib import contextmanager
from colorama import Fore, Style

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(config.BASE_DIR, config.DB_FILENAME)


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    Ensures connections are closed and rows are accessible by name.
    """
    conn = sqlite3.connect(DB_PATH)
    # Enable accessing columns by name: row['filename']
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initializes the database table and enables WAL mode for concurrency."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        with get_db_connection() as conn:
            # Enable Write-Ahead Logging (WAL) for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    filepath TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create an index on filename for faster lookups
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_filename ON processed_files(filename);"
            )
            conn.commit()

        # Security: Restrict file permissions to owner only (Linux/Mac)
        if os.name == "posix" and os.path.exists(DB_PATH):
            os.chmod(DB_PATH, 0o600)

    except sqlite3.Error as e:
        logger.error(
            f"{Fore.RED}[DB Error] Failed to initialize database: {e}{Style.RESET_ALL}"
        )
        raise


def is_file_processed(filename: str) -> bool:
    """Checks if a file has already been processed."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_files WHERE filename = ?", (filename,)
            )
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(
            f"{Fore.RED}[DB Error] Failed to check file {filename}: {e}{Style.RESET_ALL}"
        )
        return False


def add_processed_file(filename: str, filepath: str) -> None:
    """Marks a file as processed in the database."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_files (filename, filepath, processed_at) VALUES (?, ?, ?)",
                (
                    filename,
                    filepath,
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),  # Use UTC
                ),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(
            f"{Fore.RED}[DB Error] Failed to mark file as processed {filename}: {e}{Style.RESET_ALL}"
        )


def get_all_processed_filenames() -> Set[str]:
    """
    Returns a set of all processed filenames.
    WARNING: usage of this function is discouraged for large datasets.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT filename FROM processed_files")
            return {row["filename"] for row in cursor.fetchall()}
    except sqlite3.Error as e:
        logger.error(
            f"{Fore.RED}[DB Error] Failed to fetch processed filenames: {e}{Style.RESET_ALL}"
        )
        return set()


def migrate_from_logs() -> None:
    """Scans existing log files and populates the database."""
    if not os.path.exists(config.LOG_FOLDER_PATH):
        return

    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM processed_files")
            if cursor.fetchone()[0] > 0:
                return

            print(
                f"{Fore.CYAN}📦 Migrating history from logs to database...{Style.RESET_ALL}"
            )

            processed_count = 0
            # Regex is more robust than splitting by "|"
            # Captures text before the first pipe
            log_pattern = re.compile(r"^[●\s]*(.*?)\s*\|")

            conn.execute("BEGIN TRANSACTION;")  # Explicit transaction for speed

            for filename in os.listdir(config.LOG_FOLDER_PATH):
                if not filename.endswith("_daily.log"):
                    continue

                log_path = os.path.join(config.LOG_FOLDER_PATH, filename)
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if "⏳" in line:
                                match = log_pattern.match(line)
                                if match:
                                    clean_filename = match.group(1).strip()
                                    conn.execute(
                                        "INSERT OR IGNORE INTO processed_files (filename, filepath, processed_at) VALUES (?, ?, ?)",
                                        (
                                            clean_filename,
                                            "migrated_from_log",
                                            datetime.datetime.now(
                                                datetime.timezone.utc
                                            ).isoformat(),
                                        ),
                                    )
                                    processed_count += 1
                except (IOError, OSError) as e:
                    logger.warning(f"Could not read log file {filename}: {e}")

            conn.commit()

            if processed_count > 0:
                print(
                    f"{Fore.GREEN}   Done. Migrated {processed_count} records.{Style.RESET_ALL}"
                )

    except sqlite3.Error as e:
        logger.error(f"{Fore.RED}[DB Error] Migration failed: {e}{Style.RESET_ALL}")
