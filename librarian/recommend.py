"""Recommend samples using Camelot Wheel harmonic compatibility.

Works with the sample index + optional analysis cache.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .analyze import HAS_LIBROSA, analyze_file, get_compatible_keys
from .search import load_records, score, token_text


def recommend_samples(
    index_path: str | Path,
    target_key: str,
    terms: list[str] | None = None,
    category: str | None = None,
    limit: int = 20,
    analyze: bool = False,
) -> list[dict]:
    """Recommend samples harmonically compatible with a target key.

    Args:
        index_path: Path to samples_index.jsonl
        target_key: Target key (e.g., "Fm", "C", "Am")
        terms: Optional search terms to filter
        category: Optional category filter
        limit: Max results
        analyze: If True, run live pitch analysis on candidates
    """
    compatible_keys = get_compatible_keys(target_key)
    records = load_records(index_path)

    # Filter by search terms
    if terms:
        terms_lower = [t.lower() for t in terms]
        records = [
            r for r in records
            if all(t in token_text(r) for t in terms_lower)
        ]

    # Filter by category
    if category:
        records = [
            r for r in records
            if r.get("category", "").lower() == category.lower()
        ]

    if not analyze:
        # Without live analysis, just return filtered + scored results
        if terms:
            records.sort(key=lambda r: score(r, terms), reverse=True)
        return records[:limit]

    # With live analysis: check pitch compatibility
    if not HAS_LIBROSA:
        print("Warning: librosa not installed, skipping pitch analysis",
              file=sys.stderr)
        return records[:limit]

    compatible_note_names = set()
    for key in compatible_keys:
        # Extract note name (strip 'm' for minor)
        note = key.rstrip("m")
        compatible_note_names.add(note)

    scored = []
    for record in records:
        pitch_result = analyze_file(record["path"], mode="pitch")
        if pitch_result.get("is_atonal"):
            # Atonal samples (hi-hats, noise snares) are always compatible
            scored.append((record, 1.0, "atonal"))
        elif pitch_result.get("note_name") in compatible_note_names:
            scored.append((record, 2.0, pitch_result["note_name"]))
        # Non-compatible samples are skipped

    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:limit]]


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Recommend harmonically compatible samples"
    )
    parser.add_argument("key", help="Target key (e.g., Fm, C, Am)")
    parser.add_argument("terms", nargs="*", help="Optional search terms")
    parser.add_argument("--index", default="data/samples_index.jsonl")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--analyze", action="store_true",
                        help="Run live pitch analysis")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = recommend_samples(
        args.index,
        target_key=args.key,
        terms=args.terms or None,
        category=args.category,
        limit=args.limit,
        analyze=args.analyze,
    )

    compatible = get_compatible_keys(args.key)
    print(f"Target key: {args.key}")
    print(f"Compatible keys: {', '.join(compatible)}", file=sys.stderr)
    print(f"Found {len(results)} compatible samples\n")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for i, r in enumerate(results):
            print(f"  [{i}] {r['name']} [{r.get('category', '?')}] {r['path']}")


if __name__ == "__main__":
    main()
