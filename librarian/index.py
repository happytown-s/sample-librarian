"""Index audio sample folders and extract metadata.

Generalized indexer — works with any sample library structure.
Scans folders for audio files (wav, aiff, mp3, ogg, flac) and records:
- file path, name, size
- category ( inferred from parent folder name)
- readable embedded strings (for preset files like .nmsv)
- rough tags
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ROOTS = [
    "~/Music/Ableton/User Library/Samples",
    "~/Documents/Ableton Live/Samples",
]

AUDIO_EXTENSIONS = {".wav", ".aiff", ".aif", ".mp3", ".ogg", ".flac"}
PRESET_EXTENSIONS = {".nmsv", ".nksf", ".adg", ".fxp"}
PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{4,}")

# Common category names found in sample libraries
CATEGORY_SYNONYMS = {
    # Kick
    "kick": "Kick", "kicks": "Kick", "bd": "Kick", "bassdrum": "Kick",
    "bass drum": "Kick", "bassdrums": "Kick", "bottom": "Kick",
    # Snare
    "snare": "Snare", "snares": "Snare", "sd": "Snare",
    # Hi-hat
    "hihat": "Hat", "hi-hat": "Hat", "hat": "Hat", "hh": "Hat",
    # Clap
    "clap": "Clap", "claps": "Clap",
    # Percussion & World
    "perc": "Percussion", "percussion": "Percussion",
    "shaker": "Hat", "tambourine": "Hat",
    "conga": "Percussion", "congas": "Percussion", "bongo": "Percussion", "bongos": "Percussion",
    "timbale": "Percussion", "timbales": "Percussion",
    "djembe": "Percussion", "tabla": "Percussion", "cajon": "Percussion",
    "triangle": "Percussion", "cowbell": "Percussion", "cowbells": "Percussion",
    "agogo": "Percussion", "whistle": "Percussion", "guiro": "Percussion",
    "woodblock": "Percussion", "block": "Percussion",
    # Cymbal
    "cymbal": "Cymbal", "cymbals": "Cymbal",
    "crash": "Cymbal", "crashs": "Cymbal", "crashes": "Cymbal",
    "ride": "Cymbal", "rides": "Cymbal",
    "splash": "Cymbal", "splashes": "Cymbal",
    "chinese": "Cymbal", "swell": "Cymbal", "bell": "Cymbal", "bells": "Cymbal",
    # Tom
    "tom": "Tom", "toms": "Tom", "tomtom": "Tom",
    # Drum (generic — fallback for drum-specific folders without subcategory)
    "drum": "Percussion", "drums": "Percussion",
    # Rim
    "rim": "Snare", "rimshot": "Snare", "rimshots": "Snare",
    "stick": "Snare", "sticks": "Snare",
    # Hand drum
    "handdrum": "Percussion",
    # Bass
    "bass": "Bass", "sub": "Bass", "808": "Bass",
    "subbass": "Bass", "sub-bass": "Bass",
    # Synth / Lead
    "lead": "Synth", "synth": "Synth", "synths": "Synth",
    "synth note": "Synth", "synthnote": "Synth",
    # Pad / Chord
    "pad": "Pad", "pads": "Pad", "chord": "Pad", "chords": "Pad",
    # Stab / Hit
    "stab": "Synth", "stab&hit": "Synth", "stabs": "Synth",
    "hit": "Percussion", "hits": "Percussion",
    # FX
    "fx": "FX", "effect": "FX", "effects": "FX",
    "sweep": "FX", "sweep&swell": "FX",
    "riser": "FX", "risers": "FX", "fall": "FX", "falls": "FX",
    "downlifter": "FX", "uplifter": "FX", "downlift": "FX", "uplift": "FX",
    "transition": "FX", "impact": "FX", "impacts": "FX",
    "zap": "FX", "blip": "FX", "blip&blop": "FX",
    "glitch": "FX", "noise": "FX",
    "ambience": "FX", "ambient": "FX",
    "distortion": "FX", "crackle": "FX", "buzz": "FX",
    "click": "FX", "clicks": "FX",
    # Vocal
    "vocal": "Vocal", "vox": "Vocal", "voice": "Vocal", "voices": "Vocal",
    # Loop
    "loop": "Loop", "loops": "Loop",
    "combo": "Loop",
    # Metallic / Mallet
    "metallic": "Percussion", "metal": "Percussion",
    "mallet": "Percussion", "malletdrum": "Percussion",
    # Wooden
    "wooden": "Percussion", "wood": "Percussion",
    # Lick / Phrase
    "lick": "Synth", "phrase": "Synth", "phrases": "Synth",
    # Other instrument folders
    "strings": "Synth", "string": "Synth",
    "flute": "Synth", "guitar": "Synth", "piano": "Synth",
    "organ": "Synth", "brass": "Synth",
}

# Filename-only keywords (used as fallback when folder match fails)
FILENAME_CATEGORY_KEYWORDS = {
    "kick": "Kick", "kicks": "Kick", "bd ": "Kick",
    "snare": "Snare", "sd ": "Snare",
    "hihat": "Hat", "hi-hat": "Hat", "openhat": "Hat", "closedhat": "Hat",
    "ch ": "Hat", "oh ": "Hat",
    "clap": "Clap",
    "perc": "Percussion", "conga": "Percussion", "bongo": "Percussion",
    "crash": "Cymbal", "ride": "Cymbal", "splash": "Cymbal",
    "tom ": "Tom",
    "shaker": "Hat", "tamb": "Hat",
    "bass": "Bass", "sub ": "Bass", "808": "Bass",
    "synth": "Synth", "lead": "Synth",
    "pad ": "Pad", "chord": "Pad", "stab": "Synth",
    "fx ": "FX", "sweep": "FX", "riser": "FX",
    "vocal": "Vocal", "vox": "Vocal",
    "loop": "Loop",
    "rim": "Snare", "rimshot": "Snare",
    "noise": "FX", "glitch": "FX", "zap": "FX",
    "impact": "FX", "click": "FX", "blip": "FX",
}


@dataclass
class IndexConfig:
    roots: list[str] = field(default_factory=lambda: list(DEFAULT_ROOTS))
    output: str = "data/samples_index.jsonl"
    summary: str = "data/samples_summary.json"
    scan_presets: bool = True


def _resolve(path: str) -> Path:
    return Path(os.path.expanduser(path))


def _infer_category(file_path: Path) -> str:
    """Infer category from path components, then filename as fallback."""
    # 1) フォルダ名から推定
    parts = file_path.parts
    for part in reversed(parts):
        key = part.lower().replace(" ", "").replace("_", "")
        if key in CATEGORY_SYNONYMS:
            return CATEGORY_SYNONYMS[key]
    # 2) フォルダ名で見つからなかったら、部分マッチ（スペース区切りで各トークンをチェック）
    for part in reversed(parts):
        part_low = part.lower().replace("_", " ")
        for token in part_low.split():
            if token in CATEGORY_SYNONYMS:
                return CATEGORY_SYNONYMS[token]
    # 3) ファイル名からフォールバック
    name_low = file_path.stem.lower().replace("_", " ")
    for token in name_low.split():
        if token in CATEGORY_SYNONYMS:
            return CATEGORY_SYNONYMS[token]
    # 4) ファイル名内の部分文字列マッチ（短いキーワードのみ）
    for kw, cat in FILENAME_CATEGORY_KEYWORDS.items():
        if kw in name_low:
            return cat
    return "Other"


def _extract_strings(file_path: Path, max_bytes: int = 8192) -> list[str]:
    """Extract readable ASCII strings from binary files (presets)."""
    if file_path.suffix.lower() not in PRESET_EXTENSIONS:
        return []
    try:
        data = file_path.read_bytes()[:max_bytes]
        return [m.decode("ascii") for m in PRINTABLE_RE.findall(data)]
    except Exception:
        return []


def _rough_tags(name: str, category: str) -> list[str]:
    """Generate rough tags from filename."""
    tags = []
    name_lower = name.lower()
    tag_map = {
        "808": "808", "909": "909", "sub": "sub", "dark": "dark",
        "deep": "deep", "acoustic": "acoustic", "electronic": "electronic",
        "analog": "analog", "digital": "digital", "distorted": "distorted",
        "clean": "clean", "wet": "wet", "dry": "dry", "long": "long",
        "short": "short", "tight": "tight", "punchy": "punchy",
        "soft": "soft", "hard": "hard", "warm": "warm", "bright": "bright",
    }
    for keyword, tag in tag_map.items():
        if keyword in name_lower:
            tags.append(tag)
    return tags


def _scan_folder(root: Path, scan_presets: bool = True) -> Iterable[dict]:
    """Walk a folder and yield sample records."""
    extensions = AUDIO_EXTENSIONS
    if scan_presets:
        extensions = extensions | PRESET_EXTENSIONS

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in extensions:
                continue
            try:
                stat = fpath.stat()
            except OSError:
                continue

            category = _infer_category(fpath)
            name = fpath.stem
            tags = _rough_tags(name, category)
            strings = _extract_strings(fpath)

            record = {
                "name": name,
                "path": str(fpath),
                "ext": fpath.suffix.lower().lstrip("."),
                "size": stat.st_size,
                "category": category,
                "folder": fpath.parent.name,
                "root": str(root),
                "tags": tags,
                "strings": strings[:50],  # cap for index size
            }
            yield record


def build_index(config: IndexConfig) -> tuple[int, dict]:
    """Build the index and write JSONL + summary."""
    records = []
    category_counts = Counter()
    tag_counts = Counter()
    total_size = 0

    for root_str in config.roots:
        root = _resolve(root_str)
        if not root.exists():
            print(f"  ⚠ Root not found: {root}", file=sys.stderr)
            continue
        print(f"  Scanning: {root}", file=sys.stderr)
        count_before = len(records)
        for record in _scan_folder(root, config.scan_presets):
            records.append(record)
            category_counts[record["category"]] += 1
            for tag in record["tags"]:
                tag_counts[tag] += 1
            total_size += record["size"]
        print(f"    Found {len(records) - count_before} files", file=sys.stderr)

    # Write JSONL
    out_path = _resolve(config.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Write summary
    summary = {
        "total_files": len(records),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "categories": dict(category_counts.most_common()),
        "top_tags": dict(tag_counts.most_common(30)),
        "roots": config.roots,
    }
    summary_path = _resolve(config.summary)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return len(records), summary


def main():
    parser = argparse.ArgumentParser(description="Index audio sample folders")
    parser.add_argument("--root", action="append", dest="roots",
                        help="Root folder to scan (can specify multiple)")
    parser.add_argument("--out", default="data/samples_index.jsonl",
                        help="Output JSONL path")
    parser.add_argument("--summary", default="data/samples_summary.json",
                        help="Output summary JSON path")
    parser.add_argument("--no-presets", action="store_true",
                        help="Skip preset files (.nmsv, .nksf, etc.)")
    parser.add_argument("--query", action="append",
                        help="Quick query after indexing (search terms)")
    args = parser.parse_args()

    config = IndexConfig(
        roots=args.roots if args.roots else [
            os.path.expanduser(r) for r in DEFAULT_ROOTS
        ],
        output=args.out,
        summary=args.summary,
        scan_presets=not args.no_presets,
    )

    count, summary = build_index(config)
    print(f"\nIndexed {count} files ({summary['total_size_mb']} MB)")
    print(f"Categories: {', '.join(f'{k}({v})' for k, v in list(summary['categories'].items())[:10])}")

    if args.query:
        from .search import search_index
        results = search_index(config.output, args.query, limit=10)
        print(f"\nQuery {' '.join(args.query)}: {len(results)} results")
        for r in results:
            print(f"  {r['name']} [{r['category']}] — {r['path']}")


if __name__ == "__main__":
    main()
