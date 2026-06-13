# Security Notes

Sample Librarian is designed for **local-only** operation. Here's what to know.

---

## eval / exec Safe Mode

The LiveAgent integration (`live-agent-remote`) exposes `eval` and `exec` tools that execute arbitrary Python inside the Ableton Live process. These are **disabled by default** and require an explicit environment variable:

```bash
LIVEAGENT_ENABLE_UNSAFE=1
```

Without this flag, any `eval`/`exec` calls return an error. Sample Librarian itself **never calls** these tools — it only uses typed MCP commands (`import_audio_clip`, `load_sample_to_pad`, `create_drum_rack`, etc.).

**Recommendation:** Do not set `LIVEAGENT_ENABLE_UNSAFE=1` unless you fully trust the AI agent making the calls.

---

## dry_run Flag on Destructive Operations

Sample Librarian's core operations (search, analyze, recommend) are **read-only** — they never modify files on disk.

The LiveAgent integration tools that mutate Ableton Live state (`load_sample_to_pad`, `write_midi_notes`, `create_session_clip`) send commands via TCP. If your agent supports a `dry_run` or simulation mode, use it to preview actions before committing:

```python
# Example: verify sample exists and key matches before loading
result = librarian_recommend({"target_key": "Am", "category": "Kick"})
# Review result, THEN call librarian_load_to_pad
```

The `build_drum_rack_for_key()` orchestrator always reports what it loaded (`loaded_samples`) before the agent proceeds.

---

## Local-Only TCP (127.0.0.1:8765)

LiveAgent listens on `127.0.0.1:8765` by default — **localhost only**. This means:

- Only processes on the same machine can connect
- Not reachable from other devices on the LAN or internet
- No authentication is needed because the attack surface is local

**Never** change `LIVEAGENT_HOST` to `0.0.0.0` or a public IP. If you need remote access, use SSH port forwarding:

```bash
ssh -L 8765:127.0.0.1:8765 user@remote-machine
```

Config in `config.local.py`:

```python
LIVEAGENT_HOST = "127.0.0.1"  # keep this as localhost
LIVEAGENT_PORT = 8765
```

---

## config.local.py Is Gitignored

All user-specific paths and settings live in `config.local.py`, which is in `.gitignore`:

```
config.local.py
```

This file contains your local file system paths (`SAMPLES_ROOTS`) and is **never committed**. The template is `config.example.py` (copied to `config.local.py` by `setup.sh`).

**Do not** hard-code paths into `config.py` — always use `config.local.py` or environment variables:

```bash
export SAMPLES_PATH="~/Music/Samples"
export LIVEAGENT_HOST=127.0.0.1
export LIVEAGENT_PORT=8765
```

---

## Undo Group Support for Batch Operations

When an agent performs batch operations in Ableton Live (e.g., loading multiple samples via `build_drum_rack_for_key()`), each LiveAgent command opens a separate TCP connection and executes independently.

LiveAgent wraps mutations in Ableton's undo system — each command creates a single undo step. For batch operations:

- **One undo per command**: `Ctrl+Z` in Ableton reverses the last command
- **Multiple undos needed** to fully revert a `build_drum_rack_for_key()` call (it runs: create track → load kick → load snare → load hat → create clip → write notes)

If your agent needs atomicity, track the operations and reverse them explicitly, or use Ableton's undo history to step back through each action.
