#!/usr/bin/env bash
set -e

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/jrnl/plugins"

cp bin/jrnl-agenda "$HOME/.local/bin/jrnl-agenda"
cp plugins/weekly_tracker.py "$HOME/.config/jrnl/plugins/weekly_tracker.py"

chmod +x "$HOME/.local/bin/jrnl-agenda"

echo "jrnl-tools installed."
