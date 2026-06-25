"""Tests for librarian.live_agent_bridge — search/orchestration logic.

The Ableton-facing network calls (_send) are mocked so these tests run without
LiveAgent or Ableton Live. They cover the DB search phase and orchestration of
build_drum_rack_for_key.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _seed_drum_db(conn, sample_factory, upsert_analysis):
    """Seed a DB with at least one Kick, Snare, and Hat compatible with C."""
    # C-compatible keys: C, G, F, Am, Em, Dm
    sid_kick = sample_factory(
        conn, name="Kick C", category="Kick", path="/lib/kick_c.wav",
    )
    upsert_analysis(conn, sid_kick, {
        "key": "C", "pitch": "C", "note_number": 12,
        "is_atonal": False, "sample_type": "oneshot", "duration": 0.4,
    })
    sid_snare = sample_factory(
        conn, name="Snare Tight", category="Snare", path="/lib/snare.wav",
    )
    upsert_analysis(conn, sid_snare, {
        "key": "C", "pitch": "C", "note_number": 24,
        "is_atonal": False, "sample_type": "oneshot", "duration": 0.3,
    })
    # NOTE: real library uses category "Hat" (see batch_analyze_sqlite.derive_category).
    sid_hat = sample_factory(
        conn, name="Closed Hat", category="Hat", path="/lib/hat.wav",
    )
    upsert_analysis(conn, sid_hat, {
        "is_atonal": True, "sample_type": "oneshot", "duration": 0.1,
    })
    return sid_hat


def test_build_drum_rack_finds_hat_candidates(tmp_path, sample_factory, monkeypatch):
    """build_drum_rack_for_key は "Hat" カテゴリを検索し、候補を見つける。

    以前は検索カテゴリに "HiHat" を使っていたが、DB には "Hat" として格納される
    （batch_analyze_sqlite.derive_category の仕様）。そのためHat候補が常に0件だった
    バグの回帰テスト。_send をモックして検索フェーズのみを検証する。
    """
    import librarian.live_agent_bridge as lab
    from librarian.db import get_db, init_db, upsert_analysis

    db_path = str(tmp_path / "drum.db")
    init_db(db_path)
    conn = get_db(db_path)
    try:
        _seed_drum_db(conn, sample_factory, upsert_analysis)
    finally:
        conn.close()

    # LiveAgent に触れさせない: _send をスタブ化し、track_index>=0 で
    # Step2 の create_drum_rack 呼び出しを回避する。
    def _fake_send(*a, **kw):
        return {"ok": True}

    monkeypatch.setattr(lab, "_send", _fake_send)

    # Pass the test DB explicitly — otherwise build_drum_rack_for_key falls
    # back to the default data/samples.db.
    result = lab.build_drum_rack_for_key(
        "C", db_path=db_path, track_index=0, create_clip=False,
    )

    # 検索結果に Hat が含まれるべき
    assert "candidates" in result
    candidates = result["candidates"]
    assert len(candidates["HiHat"]) >= 1, (
        "Hat カテゴリが検索されず候補0件になるバグの回帰。"
        "build_drum_rack_for_key は 'Hat' を検索すべき（DB標準カテゴリ名）。"
    )
    assert candidates["HiHat"][0]["name"] == "Closed Hat"


# ---------------------------------------------------------------------------
# preview_sample: empty Live set must not raise IndexError
# ---------------------------------------------------------------------------

def test_preview_sample_empty_live_set_returns_error(monkeypatch):
    """トラック0件の空Liveセットで preview_sample は IndexError を起こさない。

    track_index < 0（自動割り当て）かつ audio トラックが1つもない場合、
    create_audio_track を呼んでも tracks が空のままだと track_index が -1 になり、
    後続の tracks[track_index] で IndexError になっていた（バグ）。
    明確なエラー結果を返すべき。
    """
    import librarian.live_agent_bridge as lab

    # LiveAgent は常に「トラック0件」の状態を返す（空のLiveセット）
    def _fake_send(command, payload=None, host="", port=0, timeout=10):
        if command == "get_live_state":
            return {"ok": True, "tracks": []}
        # create_audio_track / import_audio_clip は成功扱いだが状態は変わらない
        return {"ok": True}

    monkeypatch.setattr(lab, "_send", _fake_send)
    monkeypatch.setattr(lab, "_DEFAULT_HOST", "127.0.0.255")
    monkeypatch.setattr(lab, "_DEFAULT_PORT", 1)

    result = lab.preview_sample("/lib/kick.wav", track_index=-1, slot_index=-1)

    # IndexError ではなく、エラー情報を含む dict が返るべき
    assert isinstance(result, dict)
    assert "error" in result, (
        "空のLiveセットでは IndexError ではなく error フィールドを返すべき"
    )
