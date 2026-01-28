import pytest
import app.health as health


def test_draw_bar_0_percent():
    """Test draw_bar with 0%."""
    bar = health.draw_bar(0)
    assert "■" * 0 in bar
    assert "0%" in bar


def test_draw_bar_50_percent():
    """Test draw_bar with 50%."""
    bar = health.draw_bar(50, width=20)
    # 50% of 20 is 10
    assert "■" * 10 in bar
    assert "50%" in bar


def test_draw_bar_100_percent():
    """Test draw_bar with 100%."""
    bar = health.draw_bar(100, width=20)
    assert "■" * 20 in bar
    assert "100%" in bar


def test_suggest_model_none():
    """Test suggest_model with None inputs."""
    model, gb, desc, usage = health.suggest_model(None, None)
    assert model == "base"
    assert gb == 0.0
    assert desc == "Unknown"


def test_suggest_model_vram_low():
    """Test suggest_model with low VRAM."""
    # 4GB VRAM.
    # usable = min(4 * 0.7, 4 - 2) = min(2.8, 2.0) = 2.0 GB
    # MODEL_REQUIREMENTS: tiny(1), base(1), small(2), medium(5)...
    # small(2) / 2.0 = 1.0 (fails <= 0.7 check)
    # base(1) / 2.0 = 0.5 (passes)
    # Expected: base or tiny (sorted reverse: tiny, base... wait, sorted is large->tiny)
    # sorted: large, turbo, medium, small, base, tiny
    # Loop:
    # ...
    # small: 2/2 = 1.0 > 0.7
    # base: 1/2 = 0.5 <= 0.7 -> break.
    # Returns base.

    model, gb, desc, usage = health.suggest_model(4.0, "vram")
    assert model == "base"
    assert gb == 2.0


def test_suggest_model_vram_high():
    """Test suggest_model with high VRAM."""
    # 24GB VRAM.
    # usable = min(24 * 0.7, 24 - 2) = min(16.8, 22) = 16.8 GB
    # large(10) / 16.8 = 0.59 <= 0.7 -> returns large
    model, gb, desc, usage = health.suggest_model(24.0, "vram")
    assert model == "large"
    assert gb == pytest.approx(16.8)


def test_suggest_model_system_ram():
    """Test suggest_model with System RAM."""
    # 16GB RAM.
    # usable = 16 * 0.5 = 8.0 GB
    # turbo(6) / 8 = 0.75 > 0.7 (skip)
    # medium(5) / 8 = 0.625 <= 0.7 -> returns medium
    model, gb, desc, usage = health.suggest_model(16.0, "system")
    assert model == "medium"
    assert gb == 8.0
