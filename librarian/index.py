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
    "kick": "Kick", "kicks": "Kick", "bd": "Kick", "bassdrum": "Kick",
    "snare": "Snare", "snares": "Snare", "sd": "Snare",
    "hihat": "HiHat", "hi-hat": "HiHat", "hat": "HiHat", "hh": "HiHat",
    "clap": "Clap", "claps": "Clap",
    "perc": "Percussion", "percussion": "Percussion",
    "cymbal": "Cymbal", "crash": "Cymbal", "ride": "Cymbal", "crashs": "Cymbal",
    "tom": "Tom", "toms": "Tom",
    "shaker": "Shaker", "tambourine": "Shaker",
    "bass": "Bass", "sub": "Bass",
    "lead": "Lead", "synth": "Lead",
    "pad": "Pad", "pads": "Pad",
    "fx": "FX", "effect": "FX", "effects": "FX",
    "vocal": "Vocal", "vox": "Vocal", "voice": "Vocal",
    "loop": "Loop", "loops": "Loop",
    "one-shot": "OneShot", "oneshot": "OneShot", "one_shot": "OneShot",
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
    """Infer category from path components."""
    parts = file_path.parts
    for part in reversed(parts):
        key = part.lower().replace(" ", "").replace("_", "")
        if key in CATEGORY_SYNONYMS:
            return CATEGORY_SYNONYMS[key]
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
                "ext": fpath.suffix.lower(),
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
