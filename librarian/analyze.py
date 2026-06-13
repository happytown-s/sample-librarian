"""Audio analysis using librosa — pitch detection, BPM, key estimation.

Standalone module — does NOT require Ableton or LiveAgent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


# Camelot Wheel for harmonic mixing
CAMELOT_WHEEL = {
    # Major keys (A side)
    "G": "9A", "D": "10A", "A": "11A", "E": "12A",
    "B": "1A", "Gb": "2A", "Db": "3A", "Ab": "4A",
    "Eb": "5A", "Bb": "6A", "F": "7A", "C": "8A",
    # Minor keys (B side)
    "Em": "9B", "Bm": "10B", "F#m": "11B", "C#m": "12B",
    "G#m": "1B", "D#m": "2B", "A#m": "3B", "Fm": "4B",
    "Cm": "5B", "Gm": "6B", "Dm": "7B", "Am": "8B",
}

# Reverse lookup
CAMELOT_TO_KEY = {v: k for k, v in CAMELOT_WHEEL.items()}

# Pitch class to note name
PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F",
                     "F#", "G", "G#", "A", "A#", "B"]


def get_compatible_keys(key: str) -> list[str]:
    """Get harmonically compatible keys using Camelot Wheel.

    Compatible keys are:
    - Same key (perfect match)
    - Adjacent on same wheel (+1 / -1)
    - Relative major/minor (A ↔ B same number)
    """
    camelot = CAMELOT_WHEEL.get(key)
    if not camelot:
        return [key]

    num = int(camelot[:-1])
    letter = camelot[-1]
    compatible = []

    # Same number (relative major/minor)
    for side in ("A", "B"):
        code = f"{num}{side}"
        if code in CAMELOT_TO_KEY:
            compatible.append(CAMELOT_TO_KEY[code])

    # Adjacent numbers (same letter)
    for delta in (-1, 1):
        adj_num = ((num - 1 + delta) % 12) + 1
        code = f"{adj_num}{letter}"
        if code in CAMELOT_TO_KEY:
            compatible.append(CAMELOT_TO_KEY[code])

    return compatible


def detect_pitch(file_path: str) -> dict:
    """Detect fundamental pitch of an audio file using pyin."""
    if not HAS_LIBROSA:
        return {"error": "librosa not installed. Run: pip install librosa"}

    try:
        y, sr = librosa.load(file_path, sr=22050, mono=True)
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz("C1"),
            fmax=librosa.note_to_hz("C6"), sr=sr,
        )
        voiced = f0[voiced_flag]
        if len(voiced) == 0:
            return {
                "file": file_path,
                "pitch": None,
                "is_atonal": True,
                "note_name": None,
                "note_number": None,
                "frequency": None,
            }

        median_f0 = float(__import__("numpy").median(voiced))
        note_number = int(round(12 * __import__("numpy").log2(median_f0 / 440.0) + 69))
        note_name = PITCH_CLASS_NAMES[note_number % 12]

        return {
            "file": file_path,
            "pitch": note_name,
            "is_atonal": False,
            "note_name": note_name,
            "note_number": note_number,
            "frequency": round(median_f0, 2),
        }
    except Exception as e:
        return {"file": file_path, "error": str(e)}


def analyze_file(file_path: str, mode: str = "full") -> dict:
    """Full audio analysis: BPM, key, duration.

    mode: 'full' (BPM + key + pitch), 'pitch' (pitch only), 'bpm' (BPM only)
    """
    if not HAS_LIBROSA:
        return {"error": "librosa not installed. Run: pip install librosa"}

    try:
        import numpy as np

        if mode == "pitch":
            return detect_pitch(file_path)

        y, sr = librosa.load(file_path, sr=22050, mono=True)
        duration = len(y) / sr

        result = {
            "file": file_path,
            "duration": round(duration, 2),
            "sample_type": _classify_duration(duration),
        }

        if mode in ("full", "bpm"):
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            result["bpm"] = round(float(tempo), 1)

        if mode == "full":
            # Pitch detection
            pitch_result = detect_pitch(file_path)
            result["pitch"] = pitch_result.get("note_name")
            result["note_number"] = pitch_result.get("note_number")
            result["is_atonal"] = pitch_result.get("is_atonal", False)

            # Rough key estimation via chroma
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            chroma_mean = chroma.mean(axis=1)
            estimated_tonic = PITCH_CLASS_NAMES[int(np.argmax(chroma_mean))]
            result["estimated_key_root"] = estimated_tonic

        return result
    except Exception as e:
        return {"file": file_path, "error": str(e)}


def _classify_duration(duration: float) -> str:
    """Classify sample by duration."""
    if duration < 2:
        return "oneshot"
    elif duration < 5:
        return "short_loop"
    elif duration < 15:
        return "medium_loop"
    else:
        return "long_loop"


def analyze_folder(
    folder_path: str,
    mode: str = "pitch",
    recursive: bool = True,
) -> list[dict]:
    """Analyze all audio files in a folder."""
    folder = Path(folder_path)
    if not folder.is_dir():
        return [{"error": f"Not a directory: {folder_path}"}]

    AUDIO_EXTS = {".wav", ".aiff", ".aif", ".mp3", ".ogg", ".flac"}
    if recursive:
        files = [f for f in folder.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
    else:
        files = [f for f in folder.iterdir() if f.suffix.lower() in AUDIO_EXTS]

    results = []
    for i, f in enumerate(files):
        if i % 100 == 0 and i > 0:
            print(f"  Analyzing... {i}/{len(files)}", file=sys.stderr)
        r = analyze_file(str(f), mode=mode)
        results.append(r)

    # Sort by note number (non-atonal first, then atonal)
    if mode in ("pitch", "full"):
        results.sort(
            key=lambda r: (
                r.get("is_atonal", True),
                r.get("note_number", 999),
            )
        )

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze audio samples")
    parser.add_argument("path", help="File or folder path")
    parser.add_argument("--mode", choices=["full", "pitch", "bpm"],
                        default="full")
    parser.add_argument("--recursive", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    if path.is_file():
        result = analyze_file(str(path), mode=args.mode)
    elif path.is_dir():
        result = analyze_folder(str(path), mode=args.mode,
                                recursive=args.recursive)
    else:
        print(f"Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if isinstance(result, list):
            print(f"Analyzed {len(result)} files")
            for r in result[:20]:
                if "error" in r:
                    print(f"  ERROR: {r['file']}")
                else:
                    print(f"  {Path(r['file']).name}: "
                          f"{r.get('pitch', '?')} "
                          f"{'(atonal)' if r.get('is_atonal') else ''} "
                          f"{r.get('bpm', '')}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
