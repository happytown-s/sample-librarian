"""Search the sample index by keywords, tags, and category."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

WORD_RE = re.compile(r"[a-z0-9]+")


def load_records(index_path: str | Path) -> list[dict]:
    """Load all records from JSONL index."""
    path = Path(index_path) if not isinstance(index_path, Path) else index_path
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def token_text(record: dict) -> str:
    """Build searchable text from a record."""
    values = [
        record.get("name", ""),
        record.get("category", ""),
        record.get("folder", ""),
        " ".join(record.get("tags", [])),
        " ".join(record.get("strings", [])),
    ]
    return " ".join(v.lower() for v in values if v)


def score(record: dict, terms: list[str]) -> float:
    """Score how well a record matches the search terms."""
    text = token_text(record)
    name = record.get("name", "").lower()
    cat = record.get("category", "").lower()
    score_val = 0.0

    for term in terms:
        term_lower = term.lower()
        if term_lower in name:
            score_val += 3.0
        if term_lower == cat:
            score_val += 5.0
        if term_lower in cat:
            score_val += 2.0
        if term_lower in text:
            score_val += 1.0
        # Tag exact match bonus
        if term_lower in [t.lower() for t in record.get("tags", [])]:
            score_val += 2.0

    return score_val


def search_index(
    index_path: str | Path,
    terms: list[str],
    limit: int = 20,
    category: str | None = None,
    ext: str | None = None,
) -> list[dict]:
    """Search the index for records matching all terms."""
    records = load_records(index_path)
    terms_lower = [t.lower() for t in terms]

    results = []
    for record in records:
        text = token_text(record)
        if not all(term in text for term in terms_lower):
            continue
        if category and record.get("category", "").lower() != category.lower():
            continue
        if ext and record.get("ext", "").lower() != ext.lower():
            continue
        results.append(record)

    results.sort(key=lambda r: score(r, terms), reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Search the sample index")
    parser.add_argument("terms", nargs="+", help="Search terms (AND)")
    parser.add_argument("--index", default="data/samples_index.jsonl",
                        help="Path to index JSONL")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--ext", help="Filter by extension")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    results = search_index(
        args.index, args.terms,
        limit=args.limit, category=args.category, ext=args.ext,
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"Found {len(results)} results for: {' '.join(args.terms)}")
        for i, r in enumerate(results):
            print(f"  [{i}] {r['name']} [{r.get('category', '?')}] "
                  f"({r.get('size', 0) // 1024}KB) {r['path']}")


if __name__ == "__main__":
    main()
