#!/usr/bin/env python3
"""Re-analyze samples that failed in the first pass (no analysis_cache entry).

Uses the fixed analyze_file() with independent stage fallback so short
one-shots that failed BPM detection still get pitch/duration data.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from librarian.analyze import analyze_file
from librarian.db import get_db, upsert_analysis

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "samples.db")


def run():
    conn = get_db(DB_PATH)

    # Find samples without analysis_cache entries
    rows = conn.execute(
        "SELECT s.id, s.path FROM samples s "
        "LEFT JOIN analysis_cache a ON s.id = a.sample_id "
        "WHERE a.sample_id IS NULL"
    ).fetchall()

    total = len(rows)
    print(f"Re-analyzing {total} samples without analysis...", flush=True)

    analyzed = 0
    errors = 0
    t_start = time.time()

    for i, (sample_id, path) in enumerate(rows):
        try:
            result = analyze_file(path, mode="full")
            if "error" not in result:
                upsert_analysis(conn, sample_id, result)
                analyzed += 1
            else:
                errors += 1
        except Exception:
            errors += 1

        if (i + 1) % 100 == 0 or i == total - 1:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / rate if rate > 0 else 0
            pct = (i + 1) / total * 100
            print(
                f"[{pct:.1f}%] {i+1}/{total} | "
                f"analyzed={analyzed} err={errors} | "
                f"{rate:.1f} f/s | ETA: {remaining/60:.1f}min",
                flush=True,
            )

    elapsed = time.time() - t_start
    print(f"\nDone! {total} in {elapsed:.1f}s", flush=True)
    print(f"  Recovered: {analyzed}", flush=True)
    print(f"  Unrecoverable: {errors}", flush=True)

    # Final DB stats
    count = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    analyzed_count = conn.execute("SELECT COUNT(*) FROM analysis_cache").fetchone()[0]
    print(f"DB: {count} samples, {analyzed_count} analyzed", flush=True)
    conn.close()


if __name__ == "__main__":
    run()
