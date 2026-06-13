#!/usr/bin/env bash
set -euo pipefail

echo "=== Sample Librarian Setup ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Python check
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then
    echo "✗ Python 3 not found. Install Python 3.10+ first."
    exit 1
fi
echo "✓ Python: $($PYTHON --version)"

# Venv
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    "$PYTHON" -m venv .venv
fi
VENV_PY="$SCRIPT_DIR/.venv/bin/python3"
echo "✓ Venv: .venv/"

# Dependencies
echo "→ Installing dependencies..."
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet librosa soundfile numpy scipy mcp
echo "✓ Dependencies installed"

# Config
if [ ! -f "config.local.py" ]; then
    cp config.example.py config.local.py
    echo "✓ Created config.local.py (edit this with your sample paths!)"
else
    echo "✓ config.local.py already exists"
fi

# Data dir
mkdir -p data
echo "✓ data/ ready"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit config.local.py — set SAMPLES_ROOTS to your sample folders"
echo "  2. Build index: .venv/bin/python3 -m librarian.index --root ~/path/to/samples"
echo "  3. Search: .venv/bin/python3 -m librarian.search dark bass"
echo "  4. Optional: Install live-agent-remote for Ableton integration"
echo ""
echo "MCP server:"
echo "  .venv/bin/python3 mcp_server.py"
