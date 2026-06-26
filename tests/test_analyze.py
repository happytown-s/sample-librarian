"""Tests for librarian.analyze — pure-logic functions (no librosa required)."""

from __future__ import annotations

import math

from librarian.analyze import (  # noqa: I001
    CAMELOT_WHEEL,
    PITCH_CLASS_NAMES,
    _classify_duration,
    compute_spectral_centroid,
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


# ---------------------------------------------------------------------------
# Spectral centroid
# ---------------------------------------------------------------------------

def _sine_wave(freq, sr, n):
    """Generate n samples of a pure sine tone (pure Python, no numpy)."""
    return [math.sin(2 * math.pi * freq * t / sr) for t in range(n)]


def test_spectral_centroid_pure_tone_matches_frequency():
    """純粋な正弦波のスペクトル重心はその周波数に近い値になる。

    README は "spectral analysis" / "spectral fingerprint" を謳うが、
    analyze_file() にスペクトル重心計算が未実装で、DB列は常に空だった。
    compute_spectral_centroid は numpy が無くても動く純粋関数として切り出し、
    analyze_file から呼ぶ。CI は [dev] しか入れない（numpy/librosa 不要）。
    """
    sr = 22050
    freq = 440.0  # A4 — bins at sr/2048 ≈ 10.77Hz spacing, so 440 lands near bin 41
    n = 2048  # one analysis frame; keeps the pure-Python DFT fallback fast
    y = _sine_wave(freq, sr, n)

    centroid = compute_spectral_centroid(y, sr)
    # 正弦波の重心は周波数本身。ビン分解能と窓の影響で多少の誤差は出るので ±30Hz。
    assert abs(centroid - freq) < 30.0, f"純音 {freq}Hz の重心 {centroid:.1f} がずれすぎ"


def test_spectral_centroid_silence_is_zero():
    """無音のスペクトル重心は 0（ゼロ除算を起こさない）。"""
    y = [0.0] * 2048
    assert compute_spectral_centroid(y, 22050) == 0.0


def test_spectral_centroid_higher_for_high_frequency():
    """高周波成分を含む音の方が重心が高くなる（順序の保存）。

    重複検出 find_similar_by_spectral はこの値の近さでグループ化するため、
    音色の明るさを反映できることが重要。
    """
    sr = 22050
    n = 2048
    low = _sine_wave(110.0, sr, n)    # A2
    high = _sine_wave(2000.0, sr, n)  # ~B6

    low_c = compute_spectral_centroid(low, sr)
    high_c = compute_spectral_centroid(high, sr)
    assert high_c > low_c, "高周波音の方がスペクトル重心が高くなければならない"
