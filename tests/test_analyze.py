"""Tests for librarian.analyze — pure-logic functions (no librosa required)."""

from __future__ import annotations

from librarian.analyze import (  # noqa: I001
    CAMELOT_WHEEL,
    PITCH_CLASS_NAMES,
    _classify_duration,
    get_compatible_keys,
)

# ---------------------------------------------------------------------------
# Camelot Wheel
# ---------------------------------------------------------------------------

def test_camelot_wheel_keys():
    """Known key → Camelot code mappings are correct."""
    assert CAMELOT_WHEEL["C"] == "8A"
    assert CAMELOT_WHEEL["Am"] == "8B"
    assert CAMELOT_WHEEL["G"] == "9A"
    assert CAMELOT_WHEEL["Em"] == "9B"
    assert CAMELOT_WHEEL["Fm"] == "4B"
    assert CAMELOT_WHEEL["B"] == "1A"
    assert CAMELOT_WHEEL["Db"] == "3A"
    # Wheel should cover all 24 keys (12 major + 12 minor)
    assert len(CAMELOT_WHEEL) == 24


def test_get_compatible_keys():
    """Fm (4B) returns same, adjacent, and relative keys."""
    compat = get_compatible_keys("Fm")
    # Same number A↔B (relative major/minor): 4A = Ab
    assert "Ab" in compat
    # Adjacent on same letter (3B = A#m, 5B = Cm)
    assert "A#m" in compat
    assert "Cm" in compat
    # Self should be included too (same number B side = Fm)
    assert "Fm" in compat
    # Should have exactly 4 compatible keys
    assert len(compat) == 4


def test_get_compatible_keys_unknown_key():
    """An unknown key returns a list containing only itself."""
    assert get_compatible_keys("Xb") == ["Xb"]


# ---------------------------------------------------------------------------
# Duration classification
# ---------------------------------------------------------------------------

def test_classify_duration():
    """Duration thresholds produce correct sample types."""
    assert _classify_duration(0.1) == "oneshot"
    assert _classify_duration(1.9) == "oneshot"
    assert _classify_duration(2.0) == "short_loop"
    assert _classify_duration(4.9) == "short_loop"
    assert _classify_duration(5.0) == "medium_loop"
    assert _classify_duration(14.9) == "medium_loop"
    assert _classify_duration(15.0) == "long_loop"
    assert _classify_duration(60.0) == "long_loop"


# ---------------------------------------------------------------------------
# Pitch class names
# ---------------------------------------------------------------------------

def test_pitch_class_names():
    """PITCH_CLASS_NAMES has exactly 12 chromatic notes in the right order."""
    assert len(PITCH_CLASS_NAMES) == 12
    assert PITCH_CLASS_NAMES[0] == "C"
    assert PITCH_CLASS_NAMES[2] == "D"
    assert PITCH_CLASS_NAMES[4] == "E"
    assert PITCH_CLASS_NAMES[5] == "F"
    assert PITCH_CLASS_NAMES[7] == "G"
    assert PITCH_CLASS_NAMES[9] == "A"
    assert PITCH_CLASS_NAMES[11] == "B"
