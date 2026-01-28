import pytest
import sqlite3
from unittest.mock import patch, MagicMock
import app.config as config
import app.db as db


# Use an in-memory database for testing
@pytest.fixture
def mock_db_connection():
    # Override the DB path to use in-memory DB or temporary file
    # But since the module uses a global variable DB_PATH, we can patch `get_connection`
    # or patch `DB_PATH` if we could (but it's imported).
    # Easier is to patch `sqlite3.connect` to return our in-memory connection if the path matches,
    # or just patch `app.database.get_connection`.

    conn = sqlite3.connect(":memory:")
    with patch("app.database.get_connection", return_value=conn):
        yield conn
    conn.close()


def test_init_db(mock_db_connection):
    db.init_db()
    cursor = mock_db_connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_files';"
    )
    assert cursor.fetchone() is not None


def test_add_and_check_processed_file(mock_db_connection):
    db.init_db()
    filename = "test_audio.mp3"
    filepath = "/tmp/test_audio.mp3"

    assert db.is_file_processed(filename) is False

    db.add_processed_file(filename, filepath)

    assert db.is_file_processed(filename) is True


def test_get_all_processed_filenames(mock_db_connection):
    db.init_db()
    db.add_processed_file("file1.mp3", "/path/1")
    db.add_processed_file("file2.mp3", "/path/2")

    processed = db.get_all_processed_filenames()
    assert "file1.mp3" in processed
    assert "file2.mp3" in processed
    assert len(processed) == 2


@patch("os.path.exists")
@patch("os.listdir")
@patch("builtins.open")
def test_migrate_from_logs(mock_open, mock_listdir, mock_exists, mock_db_connection):
    db.init_db()

    # Setup mocks
    mock_exists.return_value = True
    config.LOG_FOLDER_PATH = "/mock/logs"
    mock_listdir.return_value = ["2023-01-01_daily.log"]

    # Mock file content
    mock_file = MagicMock()
    mock_file.__enter__.return_value = [
        "ignored line",
        "file_in_log.mp3 | ⏳ 1m 20s | ⏱ done in 5.0s",
        "another_file.wav | ⏳ 0m 30s | ⏱ done in 2.0s",
    ]
    mock_open.return_value = mock_file

    db.migrate_from_logs()

    processed = db.get_all_processed_filenames()
    assert "file_in_log.mp3" in processed
    assert "another_file.wav" in processed
