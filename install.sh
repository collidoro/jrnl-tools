#!/usr/bin/env bash
set -e

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/jrnl/plugins"

install_file() {
    src="$1"
    dst="$2"

    if [[ -e "$dst" ]] && cmp -s "$src" "$dst"; then
        echo "Already up to date: $dst"
        return
    fi

    cp "$src" "$dst"
    echo "Installed: $dst"
}

install_file \
    "bin/jrnl-agenda" \
    "$HOME/.local/bin/jrnl-agenda"

install_file \
    "bin/jrnl.sh" \
    "$HOME/.local/bin/jrnl.sh"

install_file \
    "plugins/weekly_tracker.py" \
    "$HOME/.config/jrnl/plugins/weekly_tracker.py"

install_file \
    "plugins/week_review.py" \
    "$HOME/.config/jrnl/plugins/week_review.py"

install_file \
    "plugins/media_player.py" \
    "$HOME/.config/jrnl/plugins/media_player.py"

chmod +x "$HOME/.local/bin/jrnl-agenda"

echo "jrnl-tools installed."
