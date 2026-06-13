---
name: sample-librarian
description: Search, analyze, and recommend audio samples via MCP. Camelot Wheel harmonic matching. Optional Ableton Live integration via live-agent-remote.
version: 1.0
---

# Sample Librarian — AI Agent Guide

## What This Does

Indexes local sample folders, lets you search by keywords, analyze audio
(pitch/BPM/key with librosa), and recommend samples harmonically compatible
with a target key using the Camelot Wheel.

**Works standalone.** Optional Ableton Live integration via
[live-agent-remote](https://github.com/happytown-s/live-agent-remote).

## MCP Tools (9 total)

### Core (always available)

- **`librarian_add_root(path, rebuild_index=True)`**
  Add a sample folder to config.local.py and auto re-index.
  Validates the path exists, prevents duplicates, persists across restarts.
  If config.local.py doesn't exist, creates it from template.
  This is the preferred way to register new sample folders — no manual file editing needed.

- **`librarian_list_roots()`**
  Show all configured sample folders with disk status and audio file counts.
  Also shows index status (exists, file count, last build time).
  Use this to check what's indexed before searching.

- **`librarian_search(terms, limit=20, category="", ext="")`**
  Search the sample index. All terms must match (AND logic).
  Returns JSON array with name, path, category, tags.

- **`librarian_index(roots, scan_presets=True)`**
  Build/rebuild the index from folder(s). Must run before search works.
  Returns summary with file counts and categories.

- **`librarian_analyze(file_path, mode="full")`**
  Analyze a single file. Modes: `"full"` (BPM+key+pitch), `"pitch"`, `"bpm"`.
  Returns pitch, note_name, note_number, BPM, duration, sample_type.

- **`librarian_analyze_folder(folder_path, mode="pitch", recursive=True)`**
  Batch analyze. Results sorted by pitch (non-atonal first).

- **`librarian_recommend(target_key, terms=None, category="", limit=20, analyze=False)`**
  Camelot Wheel recommendations. Set `analyze=True` for live pitch verification.
  Returns compatible keys + matching samples.

### Optional (requires live-agent-remote)

- **`librarian_preview(file_path, track_index=-1, slot_index=-1)`**
  Import sample as audio clip in Ableton Live for preview.

- **`librarian_load_to_pad(file_path, track_index, pad_index, ...)`**
  Load sample onto Drum Rack pad. Requires preset kit with existing chains.

Integration tools auto-detect LiveAgent. If unavailable, they return an
error with setup instructions — core tools keep working.

## Typical Workflow

```
# 1. Find compatible kicks for F minor
librarian_recommend(target_key="Fm", category="Kick", analyze=True)

# 2. Preview a candidate in Ableton
librarian_preview("/path/to/kick.wav")

# 3. Load onto Drum Rack pad 36 (C1)
librarian_load_to_pad("/path/to/kick.wav", track_index=4, pad_index=36)

# 4. (via live-agent-remote) Write a drum pattern
mcp_liveagent_write_midi_notes(track_index=4, slot_index=0, notes=[...])
```

## Camelot Wheel Reference

| Key | Camelot | Adjacent (compatible) |
|-----|---------|----------------------|
| Am  | 8B      | Gm(7B), Bm(9B), C(8A) |
| C   | 8A      | F(7A), G(9A), Am(8B) |
| Fm  | 4B      | Ebm(3B), C#m(5B), F(4A) |

**Matching rules:**
- Same number + same letter = perfect match
- ±1 same letter = smooth transition
- Same number + opposite letter = relative major/minor
- Atonal samples (hi-hats, noise) = always compatible

## Pitch Reference

| Note | MIDI 36 | MIDI 48 | MIDI 60 |
|------|---------|---------|---------|
| C    | C2      | C3      | C4 (middle C) |

Kick pitch range: MIDI 28-43 (E1-G2)
Snare pitch range: MIDI 36-55 (C2-G3)

## Sample Type Classification

| Type | Duration | Content |
|------|----------|---------|
| oneshot | < 2s | Kicks, snares, hi-hats |
| short_loop | 2-5s | Toms, bells, FX |
| medium_loop | 5-15s | Pads, strings |
| long_loop | > 15s | Ambience, phrases |

## Standard Drum Pad Map

| Pad (MIDI note) | Drum |
|-----------------|------|
| 36 (C1) | Kick |
| 38 (D1) | Snare |
| 42 (F#1) | Closed Hi-Hat |
| 46 (A#1) | Open Hi-Hat |
| 49 (C#2) | Crash |

## Pitfalls

- **Index must be built first.** Run `librarian_index` before `librarian_search`.
  If search returns empty, the index likely doesn't exist or points to wrong folders.
- **`librarian_recommend` with `analyze=True` is slow** — runs librosa on each
  candidate. Use `analyze=False` for fast keyword-based filtering first.
- **Large folders (5K+ files)** — `librarian_analyze_folder` may take minutes.
  Target smaller subfolders or use `mode="pitch"` for speed.
- **LiveAgent integration is lazy-detected** — the first call to
  `librarian_preview` or `librarian_load_to_pad` checks TCP connectivity
  (3s timeout). If Ableton is not running, returns error gracefully.
- **`load_to_pad` requires a preset kit** — empty Drum Rack pads cannot
  receive samples. Load a kit like "808 Core Kit" first via live-agent-remote.
- **Config must be set** — edit `config.local.py` with `SAMPLES_ROOTS` pointing
  to your actual sample folders before indexing.

## Configuration

Edit `config.local.py`:
```python
SAMPLES_ROOTS = ["/path/to/your/samples"]
LIVEAGENT_HOST = "127.0.0.1"
LIVEAGENT_PORT = 8765
```

Or env vars: `SAMPLES_PATH`, `LIVEAGENT_HOST`, `LIVEAGENT_PORT`.

## Registering MCP Server

### Hermes Agent
```yaml
mcp_servers:
  librarian:
    command: /path/to/.venv/bin/python3
    args: [/path/to/sample-librarian/mcp_server.py]
```

### Using with live-agent-remote
Register both servers independently:
```yaml
mcp_servers:
  liveagent:
    command: /path/to/live-agent-remote/.venv/bin/python3
    args: [/path/to/live-agent-remote/mcp_server.py]
  librarian:
    command: /path/to/sample-librarian/.venv/bin/python3
    args: [/path/to/sample-librarian/mcp_server.py]
```

The two are completely independent. Sample-librarian connects to LiveAgent
via direct TCP (not through live-agent-remote's MCP server).
