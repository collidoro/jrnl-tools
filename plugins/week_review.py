"""Interactive weekly review plugin for jrnl-agenda.

Usage:
    jrnl week review

The plugin asks seven questions sequentially and writes the answers
into the current weekly Markdown file before the first daily section.

Importing this module has no side effects.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


QUESTIONS = (
    "Wochenziele erreicht",
    "Was lief gut",
    "Was lief weniger gut",
    "Erreichte Meilensteine",
    "Hindernisse & Learnings",
    "Highlight der Woche",
    "Fokus nächste Woche",
)


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    return path.read_text(
        encoding="utf-8"
    ).splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    """Write file atomically."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = "\n".join(lines).rstrip() + "\n"

    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(text)

        os.replace(
            tmp_name,
            path,
        )

    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass

        raise


def _first_day_index(lines: list[str]) -> int:
    """Find first #### daily heading."""

    for index, line in enumerate(lines):
        if line.startswith("#### "):
            return index

    return len(lines)


def _remove_existing_review(
    lines: list[str],
) -> list[str]:
    """Remove an existing review block if present."""

    first_question = f"**{QUESTIONS[0]}**"
    last_question = f"**{QUESTIONS[-1]}**"

    start = None
    last_label = None

    for index, line in enumerate(lines):
        if line.strip() == first_question:
            start = index
            break

    if start is None:
        return lines

    for index in range(
        start,
        len(lines),
    ):
        if lines[index].strip() == last_question:
            last_label = index
            break

    if last_label is None:
        return lines

    # Last question has:
    #
    # **Fokus nächste Woche**
    # answer
    #
    end = last_label + 1

    if end < len(lines):
        end += 1

    # Consume blank lines belonging to review
    while (
        end < len(lines)
        and not lines[end].strip()
    ):
        end += 1

    return (
        lines[:start]
        + lines[end:]
    )


def _build_review(
    answers: list[str],
) -> list[str]:
    """Build Markdown review block."""

    block: list[str] = []

    for question, answer in zip(
        QUESTIONS,
        answers,
    ):
        block.append(
            f"**{question}**"
        )

        if answer:
            block.append(answer)
        else:
            block.append("")

        block.append("")

    return block


def run(
    week_path: str | Path,
    reference_day=None,
    *,
    add_next_week_goal=None,
) -> None:
    """Run interactive weekly review."""

    path = Path(week_path)

    print("")
    print("Weekly Review")
    print("")

    answers: list[str] = []

    try:
        for number, question in enumerate(
            QUESTIONS,
            start=1,
        ):
            print(
                f"{number}/7 {question}"
            )

            answer = input("> ").strip()

            answers.append(answer)

            print("")

    except (KeyboardInterrupt, EOFError):
        print("")
        print("Review abgebrochen – nichts gespeichert.")
        return

    lines = _read_lines(path)

    # Replace previous review instead of creating duplicates.
    lines = _remove_existing_review(lines)

    first_day = _first_day_index(lines)

    before = lines[:first_day]
    after = lines[first_day:]

    # Remove trailing blank lines before inserting review.
    while (
        before
        and not before[-1].strip()
    ):
        before.pop()

    review = _build_review(
        answers
    )

    result = (
        before
        + [""]
        + review
        + after
    )

    _write_lines(
        path,
        result,
    )

    next_focus = answers[-1].strip()

    if next_focus and add_next_week_goal is not None:
        add_next_week_goal(next_focus)

    print("Weekly Review gespeichert.")

__all__ = ["run"]
