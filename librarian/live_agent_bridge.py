"""Optional LiveAgent bridge — connects to live-agent-remote via TCP.

This module is OPTIONAL. It enables:
- Preview samples in Ableton Live (import audio clip)
- Load samples onto Drum Rack pads

If LiveAgent is not running or not configured, all functions raise
RuntimeError with a helpful message. The core librarian functionality
(search, analyze, recommend) works WITHOUT this module.

Setup:
1. Install live-agent-remote: https://github.com/happytown-s/live-agent-remote
2. Ensure Ableton Live is running with LiveAgent Control Surface active
3. Set LIVEAGENT_HOST and LIVEAGENT_PORT in config.local.py
"""

from __future__ import annotations

import json
import socket
from typing import Any, Optional

try:
    from .config import get_liveagent_host, get_liveagent_port
    _DEFAULT_HOST = get_liveagent_host()
    _DEFAULT_PORT = get_liveagent_port()
except Exception:
    _DEFAULT_HOST = "127.0.0.1"
    _DEFAULT_PORT = 8765


class LiveAgentNotAvailable(RuntimeError):
    """Raised when LiveAgent is not reachable."""

    def __init__(self, detail: str = ""):
        msg = (
            "LiveAgent is not available. "
            "To enable Ableton integration:\n"
            "1. Install live-agent-remote (https://github.com/happytown-s/live-agent-remote)\n"
            "2. Open Ableton Live with LiveAgent as Control Surface\n"
            "3. Set LIVEAGENT_HOST/LIVEAGENT_PORT in config.local.py"
        )
        if detail:
            msg += f"\nDetail: {detail}"
        super().__init__(msg)


def _send(
    command: str,
    payload: Optional[dict[str, Any]] = None,
    host: str = "",
    port: int = 0,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send a command to LiveAgent via TCP."""
    host = host or _DEFAULT_HOST
    port = port or _DEFAULT_PORT
    payload = payload or {}
    payload["command"] = command

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.sendall((json.dumps(payload) + "\n").encode())
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        return json.loads(data.decode().strip())
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        raise LiveAgentNotAvailable(str(e))
    finally:
        sock.close()


def is_available(host: str = "", port: int = 0) -> bool:
    """Check if LiveAgent is reachable."""
    try:
        result = _send("ping", host=host, port=port, timeout=3)
        return result.get("ok", False) or result.get("result") == "pong"
    except LiveAgentNotAvailable:
        return False


def preview_sample(
    file_path: str,
    track_index: int = -1,
    slot_index: int = -1,
    host: str = "",
    port: int = 0,
) -> dict[str, Any]:
    """Import a sample into Ableton Live for preview.

    Creates an audio clip on the specified track/slot (or auto-assigned).
    """
    # Auto-assign track if not specified
    if track_index < 0:
        state = _send("get_live_state", host=host, port=port)
        tracks = state.get("tracks", [])
        # Find or create an audio track
        audio_tracks = [
            i for i, t in enumerate(tracks)
            if t.get("type") == "audio"
        ]
        if audio_tracks:
            track_index = audio_tracks[-1]
        else:
            _send("create_audio_track", {"index": -1}, host, port)
            state = _send("get_live_state", host=host, port=port)
            track_index = len(state.get("tracks", [])) - 1

    if slot_index < 0:
        # Find next empty slot
        state = _send("get_live_state", host=host, port=port)
        tracks = state.get("tracks", [])
        if track_index < len(tracks):
            clips = tracks[track_index].get("clip_slots", [])
            slot_index = len(clips)
            for i, c in enumerate(clips):
                if not c.get("has_clip"):
                    slot_index = i
                    break

    return _send(
        "import_audio_clip",
        {
            "track_index": track_index,
            "slot_index": slot_index,
            "file_path": file_path,
        },
        host, port,
    )


def load_to_drum_pad(
    file_path: str,
    track_index: int,
    pad_index: int,
    drum_rack_index: int = 0,
    reset_effects: bool = False,
    host: str = "",
    port: int = 0,
) -> dict[str, Any]:
    """Load a sample onto a Drum Rack pad.

    Requires a preset kit with existing chains on the target pad.
    """
    return _send(
        "load_sample_to_pad",
        {
            "track_index": track_index,
            "pad_index": pad_index,
            "file_path": file_path,
            "drum_rack_index": drum_rack_index,
            "reset_effects": reset_effects,
        },
        host, port,
    )
