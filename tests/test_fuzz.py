import pytest
from hypothesis import given, strategies as st
import math
from app.utils import format_duration


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
