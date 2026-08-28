#!/usr/bin/env python3

import os
import re
import shutil
import subprocess


URL_RE = re.compile(
    r'(?:(?:https?://)?(?:www\.)?)'
    r'(?:youtu\.be/[^\s<>()]+|youtube\.com/watch\?[^\s<>()]+)',
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def find_media(lines):
    media = []

    for index, line in enumerate(lines):
        matches = URL_RE.findall(line)

        for url in matches:
            label = line.strip()

            # Wenn die URL alleine auf einer Zeile steht,
            # vorherige sinnvolle Zeile als Beschreibung verwenden.
            if label == url or label == f"- {url}":
                for previous in reversed(lines[:index]):
                    previous = previous.strip()
                    if previous:
                        label = previous.lstrip("- ").strip()
                        break

            media.append((label, normalize_url(url)))

    return media


def run(lines, reference_day=None):
    media = find_media(lines)

    if not media:
        print("Keine Medien-Links gefunden.")
        return

    if shutil.which("mpv") is None:
        print("mpv nicht gefunden.")
        return

    if len(media) == 1:
        os.execvp("mpv", ["mpv", media[0][1]])
        return

    if shutil.which("fzf") is None:
        print("fzf nicht gefunden.")
        return

    choices = "\n".join(
        f"{index + 1}\t{label}\t{url}"
        for index, (label, url) in enumerate(media)
    )

    result = subprocess.run(
        [
            "fzf",
            "--delimiter=\t",
            "--with-nth=2,3",
            "--prompt=Media > ",
        ],
        input=choices,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return

    selected = result.stdout.strip().split("\t")
    url = selected[-1]

    os.execvp("mpv", ["mpv", url])
