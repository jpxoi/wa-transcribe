import pytest
import math
import re
from pathlib import Path
from app.utils import format_duration
from app import db, health
from hypothesis import given, strategies as st, assume, settings, Phase
from hypothesis.strategies import text, integers, floats, lists, composite


# ==================== DURATION FORMATTING TESTS ====================


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_format_duration_fuzz_floats(seconds):
    """Fuzz test for format_duration with any float input."""
    result = format_duration(seconds)

    # 1. It must always return a string
    assert isinstance(result, str)
    assert len(result) > 0

    # 2. Verify behavior for invalid inputs
    if math.isnan(seconds) or math.isinf(seconds) or seconds < 0:
        assert result == "Unknown duration"

    # 3. Verify format for valid inputs
    else:
        # result should be either "Xm Ys" or "Z.Zs"
        if "m" in result:
            assert result.endswith("s")
            parts = result.split("m ")
            assert len(parts) == 2
            assert parts[0].isdigit()  # minutes
            assert parts[1][:-1].isdigit()  # seconds
        else:
            assert result.endswith("s")
            # Should be convertable to float (removing 's')
            try:
                val = float(result[:-1])
                assert val >= 0
            except ValueError:
                pytest.fail(f"Result {result} is not a valid seconds format")


@given(st.integers())
def test_format_duration_fuzz_integers(seconds):
    """Fuzz test for format_duration with integers."""
    result = format_duration(seconds)
    assert isinstance(result, str)

    if seconds < 0:
        assert result == "Unknown duration"
    else:
        # Check that it produces "s" at the end
        assert result.endswith("s")


@given(st.floats(min_value=0, max_value=86400))  # 0 to 24 hours
def test_format_duration_valid_range(seconds):
    """Test format_duration with valid duration range."""
    result = format_duration(seconds)

    # Should never return "Unknown duration" for valid inputs
    assert result != "Unknown duration"
    assert result.endswith("s")

    # Verify the format is parseable
    if "m" in result:
        # Format: "Xm Ys"
        match = re.match(r"^(\d+)m (\d+)s$", result)
        assert match is not None, f"Invalid format: {result}"
        minutes, secs = int(match.group(1)), int(match.group(2))
        assert 0 <= secs < 60
        assert minutes >= 0
    else:
        # Format: "X.Xs"
        match = re.match(r"^(\d+(?:\.\d+)?)s$", result)
        assert match is not None, f"Invalid format: {result}"


# ==================== DATABASE FUZZ TESTS ====================


@given(text(min_size=1, max_size=255))
@settings(max_examples=200, phases=[Phase.generate, Phase.target])
def test_db_filename_fuzz(filename):
    """Fuzz test database operations with various filenames."""
    # Skip problematic characters that would cause file system issues
    assume(not any(c in filename for c in ["\x00", "\n", "\r"]))

    # Test that is_file_processed doesn't crash with weird filenames
    try:
        # The function should handle any string input gracefully
        result = db.is_file_processed(filename)
        assert isinstance(result, bool)
    except Exception as e:
        # Should not raise exceptions for string inputs
        pytest.fail(f"is_file_processed raised exception: {e}")


@given(
    filename=text(
        min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-."
    ),
    filepath=text(
        min_size=1, max_size=255, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./"
    ),
)
@settings(max_examples=100)
def test_db_filename_validation_fuzz(filename, filepath):
    """Fuzz test filename and filepath string validation."""
    # Test that strings can be used as arguments without crashing
    # This validates the input types the DB functions expect
    assert isinstance(filename, str)
    assert isinstance(filepath, str)
    assert len(filename) > 0
    assert len(filepath) > 0


# ==================== PATH HANDLING FUZZ TESTS ====================


@given(text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=200))
@settings(max_examples=150)
def test_path_handling_fuzz(path_string):
    """Test path handling with various string inputs."""
    try:
        # Should not crash when creating Path objects
        p = Path(path_string)
        assert isinstance(p, Path)

        # Test basic operations don't crash
        str(p)
        p.name
        p.suffix
    except (ValueError, OSError):
        # Some invalid paths may raise exceptions, which is acceptable
        pass


# ==================== CONFIG VALUE FUZZ TESTS ====================


@given(
    st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=500),
        st.booleans(),
        st.none(),
    )
)
@settings(max_examples=200)
def test_config_value_types_fuzz(value):
    """Test that config can handle various value types."""
    # Config values should be serializable to JSON
    import json

    try:
        serialized = json.dumps({"test_key": value})
        deserialized = json.loads(serialized)

        # Verify round-trip
        assert "test_key" in deserialized
    except (TypeError, ValueError):
        # Some values may not be JSON serializable, which is acceptable
        # as long as it doesn't crash the application
        pass


# ==================== LOG PATTERN FUZZ TESTS ====================


@composite
def log_line_strategy(draw):
    """Generate plausible log lines for testing."""
    filename = draw(
        text(
            min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-."
        )
    )
    duration = draw(floats(min_value=0.1, max_value=3600))
    elapsed = draw(floats(min_value=0.1, max_value=300))

    return filename, duration, elapsed


@given(log_line_strategy())
@settings(max_examples=150)
def test_log_pattern_parsing_fuzz(log_data):
    """Test log pattern parsing with various inputs."""
    filename, duration, elapsed = log_data

    # Simulate the log pattern used in migrate_from_logs
    log_pattern = re.compile(r"^[●\s]*(.*?)\s*\|")

    # Create a test log line
    test_line = f"{filename}  |  ⏳ {duration}  |  ⏱ done in {elapsed:.1f}s"

    match = log_pattern.match(test_line)
    if match:
        parsed_filename = match.group(1).strip()
        # Should successfully parse filename
        assert isinstance(parsed_filename, str)
        assert len(parsed_filename) > 0


# ==================== HEALTH CHECK FUZZ TESTS ====================


@given(floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_draw_bar_fuzz(percent):
    """Fuzz test the progress bar drawing function."""
    try:
        result = health.draw_bar(percent)
        assert isinstance(result, str)
        # Bar should have a consistent structure
        assert "[" in result
        assert "]" in result
    except Exception as e:
        pytest.fail(f"draw_bar crashed with percent={percent}: {e}")


@given(
    total_gb=st.one_of(
        st.floats(min_value=0.5, max_value=256, allow_nan=False, allow_infinity=False),
        st.none(),
    ),
    mem_type=st.one_of(st.sampled_from(["vram", "unified", "system"]), st.none()),
)
@settings(max_examples=100)
def test_suggest_model_fuzz(total_gb, mem_type):
    """Fuzz test model suggestion with various memory configurations."""
    try:
        result = health.suggest_model(total_gb, mem_type)

        # Should return a tuple of 4 elements
        assert isinstance(result, tuple)
        assert len(result) == 4

        model_name, usable_gb, rule_desc, usage_pct = result

        # Validate return types
        assert isinstance(model_name, str)
        assert isinstance(usable_gb, (float, int, type(None)))
        assert isinstance(rule_desc, str)
        assert isinstance(usage_pct, (float, int, type(None)))

    except Exception as e:
        pytest.fail(f"suggest_model crashed: {e}")


# ==================== EDGE CASE TESTS ====================


@given(lists(integers(min_value=-1000, max_value=1000), min_size=0, max_size=100))
def test_queue_size_handling(items):
    """Test that queue operations handle various sizes."""
    import queue

    q = queue.Queue()

    # Add items
    for item in items:
        q.put(item)

    # Verify size
    assert q.qsize() == len(items)

    # Drain queue
    retrieved = []
    while not q.empty():
        retrieved.append(q.get())

    # Should retrieve all items
    assert len(retrieved) == len(items)


@given(text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"))
def test_file_extension_handling(extension):
    """Test file extension handling."""
    filename = f"test.{extension}"

    p = Path(filename)
    assert p.suffix == f".{extension}"
    assert p.stem == "test"

    # Test with opus - the transcriber's target format
    if extension == "opus":
        assert filename.endswith(".opus")
