# Troubleshooting

---

## LiveAgent Connection Refused

**Symptom:** `librarian_preview` or `librarian_load_to_pad` returns:

```json
{"error": "LiveAgent not available. Install live-agent-remote..."}
```

**Checklist:**

1. **Is Ableton Live open?** LiveAgent requires Live to be running.
2. **Is the LiveAgent Control Surface active?** In Live: Preferences → Link/Tempo/MIDI → Control Surface list should include "LiveAgent".
3. **Is the TCP server running?** The LiveAgent Remote script starts a TCP listener on `127.0.0.1:8765` when Live loads it.
4. **Port mismatch?** Check `config.local.py`:
   ```python
   LIVEAGENT_HOST = "127.0.0.1"
   LIVEAGENT_PORT = 8765
   ```
5. **Test the connection directly:**
   ```bash
   echo '{"command": "ping"}' | nc 127.0.0.1 8765
   ```
   Should return `{"ok": true, ...}`.

Core tools (search, analyze, recommend) work **without** LiveAgent — only preview and pad-loading require it.

---

## librosa Not Installed

**Symptom:** Analysis tools return:

```json
{"error": "librosa not installed. Run: pip install librosa"}
```

**Fix:**

```bash
# Using the project venv
.venv/bin/pip install librosa soundfile numpy scipy

# Or re-run setup
bash setup.sh
```

`librosa` is listed in `setup.sh` but may fail to install on some systems. Common issues:

- **macOS (Apple Silicon):** Ensure Rosetta 2 or use the arm64 wheel: `pip install --upgrade librosa`
- **Linux:** May need system packages: `sudo apt install libsndfile1 ffmpeg`

When librosa is unavailable, search and index still work — only analysis (pitch/BPM/key) and `recommend(analyze=True)` are affected.

---

## Empty Search Results (Need to Index First)

**Symptom:** `librarian_search` returns `[]` for any query.

**Cause:** The index hasn't been built, or no roots are configured.

**Fix:**

1. **Check configured roots and index status:**
   ```json
   librarian_list_roots()
   ```
   Verify `index.exists` is `true` and `indexed_files > 0`.

2. **If no roots configured** — add one:
   ```json
   librarian_add_root({"path": "~/Music/Samples"})
   ```

3. **If roots exist but index is empty** — rebuild:
   ```json
   librarian_index({"roots": ["~/Music/Samples"]})
   ```

4. **For SQLite DB search** (used by `build_drum_rack_for_key`):
   ```bash
   python3 -m librarian.db --jsonl data/samples_index.jsonl --stats
   ```
   This initializes `data/samples.db` and migrates records from the JSONL index.

---

## FTS5 Not Available (Older SQLite)

**Symptom:** `init_db()` fails with:

```
sqlite3.OperationalError: no such module: fts5
```

**Cause:** Your system's SQLite library was compiled without FTS5 support. This affects older macOS (pre-12) and some Linux distros.

**Fix:**

```bash
# Check if FTS5 is available
python3 -c "import sqlite3; sqlite3.connect(':memory:').execute('CREATE VIRTUAL TABLE t USING fts5(x)')"

# If it fails, install a newer SQLite via Homebrew (macOS)
brew install sqlite3

# Or use the Python bundle that includes its own SQLite
pip install pysqlite3-binary
```

Then set the environment variable to use the bundled version:

```bash
export SQLITE_USE_PYSQLITE3=1
```

**Minimum SQLite version:** 3.24.0 (for `ON CONFLICT DO UPDATE` upsert support). FTS5 requires 3.9.0+.

---

## Ableton Drum Rack Pad Has No Chain

**Symptom:** `librarian_load_to_pad` succeeds but no sound plays, or LiveAgent reports an error loading to a pad.

**Cause:** The target Drum Rack pad has no chain/device. The `load_sample_to_pad` technique replaces the first instrument device in an existing chain — it can't create one from scratch.

**Fix:**

1. **Use a preset kit** — `build_drum_rack_for_key()` defaults to `"808 Core Kit.adg"`, which has chains on pads 36–51. Always pass a kit name that has pre-built chains.

2. **Create a Drum Rack with a template:**
   ```json
   // Via LiveAgent
   create_drum_rack({"kit_name": "808 Core Kit.adg"})
   ```

3. **Verify pad structure:**
   ```json
   inspect_drum_rack({"track_index": 0, "pad_range": [36, 42]})
   ```
   Each pad should show a chain with at least one device.

4. **Pad MIDI note map** (standard layout):
   - 36 (C1) = Kick
   - 38 (D1) = Snare
   - 42 (F#1) = Closed Hat
   - 46 (A#1) = Open Hat

---

## Symlinked Samples Pointing to Unmounted Drives

**Symptom:** Search returns a sample path, but `librarian_preview` or `librarian_analyze` fails with `FileNotFoundError` or `librosa.util.exceptions.ParameterError`.

**Cause:** The indexed path is a symlink to an external drive that's no longer mounted. This is common with sample libraries stored on external SSDs or network shares.

**Diagnosis:**

```bash
# Check if the path resolves
ls -la /path/to/indexed/sample.wav

# Find broken symlinks in a root
find ~/Music/Samples -type l ! -exec test -e {} \; -print
```

**Fix:**

1. **Remount the drive** and re-run the operation.
2. **Re-index after remounting** to update any stale paths:
   ```json
   librarian_index({"roots": ["~/Music/Samples"]})
   ```
3. **Remove broken entries** from the SQLite DB:
   ```python
   from librarian.db import get_db
   conn = get_db("data/samples.db")
   conn.execute("DELETE FROM samples WHERE path NOT IN (SELECT path FROM samples WHERE 1=1)")
   # Or selectively: DELETE FROM samples WHERE path LIKE '/Volumes/OldDrive/%'
   conn.commit()
   conn.close()
   ```
4. **Prevent future issues:** Add a path-existence check to `config.local.py` roots that validates on startup, or use `librarian_list_roots()` which reports `exists: false` for missing roots.
