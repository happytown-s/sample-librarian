# Recipes

Common usage patterns for Sample Librarian.

---

## Search for Compatible Kicks in Fm

Use Camelot Wheel matching to find kicks that fit an Fm track.

**MCP tool:**

```json
librarian_recommend({
  "target_key": "Fm",
  "category": "Kick",
  "limit": 10,
  "analyze": true
})
```

Returns Fm-compatible keys (`Dbm`, `C#m`, `EbM`, `Abm`, `F`) plus ranked kick samples. Set `analyze: true` for live pitch verification via librosa (slower but precise).

**CLI:**

```bash
python3 -m librarian.recommend Fm kick --category Kick --analyze
```

---

## Build a Drum Rack for Am with One Command

The `build_drum_rack_for_key()` function does everything in one shot: search → create Drum Rack → load samples → write MIDI pattern.

```python
from librarian.live_agent_bridge import build_drum_rack_for_key

result = build_drum_rack_for_key(
    target_key="Am",
    pattern="2step",    # "2step", "4floor", or "trap"
    track_index=-1,     # -1 = create new track at end
    kit_name="808 Core Kit.adg",
)
```

This will:
1. Search the DB for Am-compatible kicks, snares, and hats
2. Create a Drum Rack track with the 808 Core Kit
3. Load the best sample onto each pad (36=kick, 38=snare, 42=hat)
4. Create a 1-bar MIDI clip with the chosen pattern

**Requirements:** LiveAgent running, `data/samples.db` populated.

---

## Find Duplicate Samples

After indexing, detect exact and near-duplicates from the database:

```python
from librarian.db import get_db, find_all_duplicates

conn = get_db("data/samples.db")
report = find_all_duplicates(conn)
conn.close()
```

Returns four categories:

- **`by_hash`** — content-identical files (same `file_hash`)
- **`by_duration`** — near-identical durations (±0.05s, same category)
- **`by_pitch`** — same fundamental pitch + sample type
- **`by_spectral`** — similar timbre (spectral centroid within 50 Hz)

Each group includes full sample paths so you can review and delete duplicates manually.

---

## Index a New Sample Folder

**Via MCP (persists to config + auto re-index):**

```json
librarian_add_root({
  "path": "~/Music/Samples/My New Pack",
  "rebuild_index": true
})
```

This adds the path to `config.local.py` and scans all configured roots immediately.

**Via CLI (one-off, no config change):**

```bash
python3 -m librarian.index --root ~/Music/Samples/My\ New\ Pack
```

**To also populate the SQLite DB:**

```bash
# Initialize DB and migrate from JSONL
python3 -m librarian.db --jsonl data/samples_index.jsonl --stats
```

---

## Preview a Sample in Ableton

Import a sample as an audio clip to audition it:

```json
librarian_preview({
  "file_path": "/path/to/kick.wav",
  "track_index": -1,
  "slot_index": -1
})
```

Track and slot set to `-1` auto-assign to the last audio track and next empty clip slot. A new audio track is created if none exists.

**Requirements:** LiveAgent running with Ableton Live open.

---

## Analyze a Folder for Pitch

Batch-detect fundamental pitch across all audio files in a folder. Results are sorted by note number (tonal first, atonal last).

```json
librarian_analyze_folder({
  "folder_path": "~/Music/Samples/Kicks",
  "mode": "pitch",
  "recursive": true
})
```

Each result includes `pitch`, `note_name`, `note_number`, `frequency`, `is_atonal`, and `sample_type` (`oneshot` / `short_loop` / `medium_loop` / `long_loop`).

**CLI:**

```bash
python3 -m librarian.analyze ~/Music/Samples/Kicks --mode pitch --json
```

Use `mode: "full"` to also get BPM and estimated key root via chroma analysis.
