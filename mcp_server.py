"""MCP Server for Sample Librarian.

Exposes 7 tools for AI agents to search, analyze, and recommend samples.
Optionally integrates with live-agent-remote for Ableton Live preview.

Core tools (always available):
  - librarian_search       — Search sample index by keywords
  - librarian_index        — Build/rebuild the sample index
  - librarian_analyze      — Analyze audio file (pitch, BPM, key)
  - librarian_analyze_folder — Batch analyze a folder
  - librarian_recommend    — Recommend key-compatible samples

Integration tools (require live-agent-remote running):
  - librarian_preview       — Preview sample in Ableton Live
  - librarian_load_to_pad   — Load sample onto Drum Rack pad
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure we can import the librarian package
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from librarian.index import build_index, IndexConfig
from librarian.search import search_index, load_records
from librarian.analyze import analyze_file, analyze_folder, get_compatible_keys
from librarian.recommend import recommend_samples

# Check LiveAgent availability lazily
_LIVEAGENT_CHECKED = False
_LIVEAGENT_AVAILABLE = False


def _check_liveagent() -> bool:
    global _LIVEAGENT_CHECKED, _LIVEAGENT_AVAILABLE
    if _LIVEAGENT_CHECKED:
        return _LIVEAGENT_AVAILABLE
    _LIVEAGENT_CHECKED = True
    try:
        from librarian.live_agent_bridge import is_available
        _LIVEAGENT_AVAILABLE = is_available()
    except Exception:
        _LIVEAGENT_AVAILABLE = False
    return _LIVEAGENT_AVAILABLE


def _get_index_path() -> str:
    """Get the index path from config or default."""
    try:
        from librarian.config import get_index_path
        return get_index_path()
    except Exception:
        return str(Path(__file__).parent / "data" / "samples_index.jsonl")


if not HAS_MCP:
    print("MCP package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("sample-librarian")


# ─── Core Tools ───

@mcp.tool()
def librarian_search(
    terms: list[str],
    limit: int = 20,
    category: str = "",
    ext: str = "",
) -> str:
    """Search the sample index by keywords.

    Args:
        terms: Search terms (all must match, AND logic)
        limit: Max results (default 20)
        category: Filter by category (e.g., "Kick", "Snare")
        ext: Filter by extension (e.g., ".wav")

    Returns:
        JSON array of matching samples with name, path, category, tags.
    """
    results = search_index(
        _get_index_path(), terms,
        limit=limit,
        category=category or None,
        ext=ext or None,
    )
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def librarian_index(
    roots: list[str],
    scan_presets: bool = True,
) -> str:
    """Build or rebuild the sample index from folder(s).

    Args:
        roots: List of root folders to scan
        scan_presets: Include preset files (.nmsv, .nksf, etc.)

    Returns:
        JSON summary with total files, categories, sizes.
    """
    config = IndexConfig(
        roots=roots,
        output=_get_index_path(),
        scan_presets=scan_presets,
    )
    count, summary = build_index(config)
    return json.dumps(summary, ensure_ascii=False)


@mcp.tool()
def librarian_analyze(
    file_path: str,
    mode: str = "full",
) -> str:
    """Analyze a single audio file.

    Args:
        file_path: Path to audio file
        mode: 'full' (BPM + key + pitch), 'pitch' (pitch only), 'bpm' (BPM only)

    Returns:
        JSON with pitch, BPM, key, duration, sample_type.
    """
    result = analyze_file(file_path, mode=mode)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def librarian_analyze_folder(
    folder_path: str,
    mode: str = "pitch",
    recursive: bool = True,
) -> str:
    """Analyze all audio files in a folder.

    Args:
        folder_path: Path to folder
        mode: 'full', 'pitch', or 'bpm'
        recursive: Scan subdirectories

    Returns:
        JSON array of analysis results, sorted by pitch.
    """
    results = analyze_folder(folder_path, mode=mode, recursive=recursive)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def librarian_recommend(
    target_key: str,
    terms: list[str] | None = None,
    category: str = "",
    limit: int = 20,
    analyze: bool = False,
) -> str:
    """Recommend samples harmonically compatible with a target key.

    Uses Camelot Wheel matching (adjacent keys ±1, relative major/minor).

    Args:
        target_key: Target key (e.g., "Fm", "C", "Am")
        terms: Optional search terms to filter
        category: Filter by category
        limit: Max results
        analyze: Run live pitch analysis for precise matching

    Returns:
        JSON array of recommended samples.
    """
    results = recommend_samples(
        _get_index_path(),
        target_key=target_key,
        terms=terms,
        category=category or None,
        limit=limit,
        analyze=analyze,
    )
    compatible = get_compatible_keys(target_key)
    output = {
        "target_key": target_key,
        "compatible_keys": compatible,
        "results": results,
    }
    return json.dumps(output, ensure_ascii=False)


# ─── LiveAgent Integration Tools (optional) ───

@mcp.tool()
def librarian_preview(
    file_path: str,
    track_index: int = -1,
    slot_index: int = -1,
) -> str:
    """Preview a sample in Ableton Live.

    Requires live-agent-remote running with Ableton Live open.
    Creates an audio clip on the specified (or auto-assigned) track/slot.

    Args:
        file_path: Path to audio sample
        track_index: Target track (-1 = auto-assign audio track)
        slot_index: Target clip slot (-1 = auto-assign next empty)

    Returns:
        JSON result from LiveAgent.
    """
    if not _check_liveagent():
        return json.dumps({
            "error": (
                "LiveAgent not available. Install live-agent-remote "
                "and ensure Ableton Live is running with LiveAgent active."
            )
        })
    from librarian.live_agent_bridge import preview_sample
    result = preview_sample(file_path, track_index, slot_index)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def librarian_load_to_pad(
    file_path: str,
    track_index: int,
    pad_index: int,
    drum_rack_index: int = 0,
    reset_effects: bool = False,
) -> str:
    """Load a sample onto a Drum Rack pad in Ableton Live.

    Requires live-agent-remote with a preset Drum Kit loaded.
    Uses hotswap_target technique to swap samples without destroying the rack.

    Args:
        file_path: Path to audio sample
        track_index: Track containing the Drum Rack
        pad_index: MIDI note number for the pad (36=C1 kick, 38=snare)
        drum_rack_index: Device index of Drum Rack (default 0)
        reset_effects: Clear effects chain after loading

    Returns:
        JSON result from LiveAgent.
    """
    if not _check_liveagent():
        return json.dumps({
            "error": (
                "LiveAgent not available. Install live-agent-remote "
                "and ensure Ableton Live is running with LiveAgent active."
            )
        })
    from librarian.live_agent_bridge import load_to_drum_pad
    result = load_to_drum_pad(
        file_path, track_index, pad_index,
        drum_rack_index=drum_rack_index,
        reset_effects=reset_effects,
    )
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
