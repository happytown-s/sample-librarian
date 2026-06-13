"""Configuration template — copy to config.local.py and edit."""

# Root folders to scan for samples
SAMPLES_ROOTS = [
    # "~/Music/Ableton/User Library/Samples",
    # "~/Documents/Ableton Live/Samples",
    # "/path/to/your/sample/library",
]

# Index output paths
INDEX_PATH = "data/samples_index.jsonl"
SUMMARY_PATH = "data/samples_summary.json"

# ─── Optional: LiveAgent Integration ───
# To enable Ableton Live integration, install live-agent-remote:
# https://github.com/happytown-s/live-agent-remote
LIVEAGENT_HOST = "127.0.0.1"
LIVEAGENT_PORT = 8765
