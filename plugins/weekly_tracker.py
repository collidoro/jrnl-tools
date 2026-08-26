"""Weekly tracker plugin for jrnl-agenda.

- f p k l m n e -> key letter when active
- r             -> sleep duration as number
- d             -> colored dot according to daily rating

Inactive cells show their row key in dark gray.
Active normal cells show their row key in white.

Importing this module has no side effects.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from collections.abc import Sequence
from typing import TextIO


# ==========================================================
# CONFIG
# ==========================================================

WEEKDAYS = ("M", "D", "M", "D", "F", "S", "S")
ROWS = ("f", "p", "k", "l", "m", "n", "e", "r", "d")

RESET = "\033[0m"

# Dark gray
DIM = "\033[38;2;77;77;77m"

# White for active keys
WHITE = "\033[38;2;255;255;255m"

# Original Dataview colors for row d
D_COLORS = {
    "-": "\033[38;2;182;210;180m",
    "/": "\033[38;2;139;191;210m",
    "\\": "\033[38;2;255;185;182m",
}


# ==========================================================
# PARSER
# ==========================================================

_DAY_HEADING = re.compile(
    r"^####\s+(?:Mo|Di|Mi|Do|Fr|Sa|So)\s+"
    r"(\d{2})\.(\d{2})\.(\d{2})\s*$"
)

_R_LINE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:_r_|r)\b",
    re.IGNORECASE,
)

_EVENT_LINE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:_e_|e)(?:\s|$)",
    re.IGNORECASE,
)

_F_LINE = re.compile(
    r"^\s*f(?:\s|$)",
    re.IGNORECASE,
)

_MARKER_LINE = re.compile(
    r"^(?:_r_|r|_e_|e|w|f)(?:\s|$)",
    re.IGNORECASE,
)

_TASK_LINE = re.compile(
    r"^-\s*\[[ xX]\]"
)


def _date_from_heading(line: str) -> dt.date | None:
    match = _DAY_HEADING.match(line.strip())

    if not match:
        return None

    day, month, short_year = map(int, match.groups())

    try:
        return dt.date(
            2000 + short_year,
            month,
            day,
        )
    except ValueError:
        return None


def _split_day_sections(
    lines: Sequence[str],
) -> dict[dt.date, list[str]]:
    """Split a weekly Markdown file into daily sections."""

    sections: dict[dt.date, list[str]] = {}

    current_date: dt.date | None = None
    current_lines: list[str] = []

    def save_current() -> None:
        if current_date is not None:
            sections[current_date] = current_lines.copy()

    for line in lines:
        heading_date = _date_from_heading(line)

        if heading_date is not None:
            save_current()

            current_date = heading_date
            current_lines = [line]

        elif current_date is not None:

            if line.startswith("#### "):
                save_current()

                current_date = None
                current_lines = []

            else:
                current_lines.append(line)

    save_current()

    return sections


def _content_lines(
    section: Sequence[str],
) -> list[str]:
    """Remove heading, YAML and fenced code from parser input."""

    result: list[str] = []

    in_code = False
    in_yaml = False
    first_content = True

    for index, raw in enumerate(section):
        stripped = raw.strip()

        if index == 0 and stripped.startswith("#### "):
            continue

        if first_content and stripped == "---":
            in_yaml = True
            first_content = False
            continue

        first_content = False

        if in_yaml:
            if stripped == "---":
                in_yaml = False
            continue

        if stripped.startswith("```"):
            in_code = not in_code
            continue

        if not in_code:
            result.append(raw)

    return result


def parse_day(
    section: Sequence[str],
) -> dict[str, object]:
    """Return tracker values for one day."""

    lines = _content_lines(section)

    record: dict[str, object] = {}

    # ------------------------------------------------------
    # r line
    # ------------------------------------------------------

    r_candidates = [
        line
        for line in lines
        if _R_LINE.match(line)
    ]

    r_line = (
        r_candidates[-1]
        if r_candidates
        else None
    )

    if r_line is not None:

        # Sleep duration
        sleep = re.search(
            r"\b(?:_r_|r)\b\s*[:\-]?\s*"
            r"([0-9]+(?:[.,][0-9]+)?)",
            r_line,
            re.IGNORECASE,
        )

        if sleep:
            record["r"] = float(
                sleep.group(1).replace(",", ".")
            )

        # Compact flags
        for token in re.split(
            r"[^A-Za-z]+",
            r_line,
        ):
            key = token.lower()

            if key in {
                "f",
                "p",
                "k",
                "l",
                "m",
            }:
                record[key] = True

        # Daily rating
        rating = re.search(
            r"([/\\-])\s*$",
            r_line,
        )

        if rating:
            record["d"] = rating.group(1)

    # ------------------------------------------------------
    # f
    # ------------------------------------------------------

    if any(
        _F_LINE.match(line)
        for line in lines
    ):
        record["f"] = True

    # ------------------------------------------------------
    # e
    # ------------------------------------------------------

    if any(
        _EVENT_LINE.match(line)
        for line in lines
    ):
        record["e"] = True

    # ------------------------------------------------------
    # n
    # ------------------------------------------------------

    for raw in lines:
        stripped = raw.strip()

        if not stripped:
            continue

        if _MARKER_LINE.match(stripped):
            continue

        if _TASK_LINE.match(stripped):
            continue

        if re.match(
            r"^x\s+",
            stripped,
        ):
            continue

        paragraph = (
            re.match(
                r"^[A-Za-zÀ-ÿ0-9]",
                stripped,
            )
            is not None
            and len(stripped.split()) >= 5
        )

        bullet = False

        if re.match(
            r"^-\s+",
            stripped,
        ):
            body = re.sub(
                r"^-\s+",
                "",
                stripped,
            )

            bullet = len(body.split()) >= 4

        if paragraph or bullet:
            record["n"] = True
            break

    return record


# ==========================================================
# CELL CONTENT
# ==========================================================

def _cell(
    row: str,
    record: dict[str, object],
    use_color: bool,
) -> str:

    # Sleep duration
    if row == "r":
        sleep = record.get("r")

        if isinstance(sleep, (int, float)):
            return f"{sleep:g}"

        if use_color:
            return f"{DIM}r{RESET}"

        return "r"

    # Daily rating
    if row == "d":
        rating = record.get("d")

        if rating in D_COLORS:
            if use_color:
                return (
                    f"{D_COLORS[rating]}"
                    f"●"
                    f"{RESET}"
                )

            return "●"

        if use_color:
            return f"{DIM}d{RESET}"

        return "d"

    # Normal rows:
    # active = white key
    # inactive = dark-gray key
    if row in record:
        if use_color:
            return f"{WHITE}{row}{RESET}"

        return row

    if use_color:
        return f"{DIM}{row}{RESET}"

    return row


# ==========================================================
# RENDER
# ==========================================================

def render(
    week_lines: Sequence[str],
    reference_day: dt.date,
    *,
    use_color: bool = True,
) -> str:
    """Render the weekly tracker as a compact table."""

    iso = reference_day.isocalendar()

    days = [
        dt.date.fromisocalendar(
            int(iso.year),
            int(iso.week),
            weekday,
        )
        for weekday in range(1, 8)
    ]

    sections = _split_day_sections(
        week_lines
    )

    records = [
        parse_day(
            sections.get(day, ())
        )
        for day in days
    ]

    # Same width as the existing jrnl-agenda separator:
    #
    # --------------------------------------------
    WIDTH = 44

    # Center position of each weekday/cell.
    POSITIONS = (
        1,
        7,
        13,
        19,
        25,
        31,
        37,
    )

    output: list[str] = []

    # ------------------------------------------------------
    # Header
    # ------------------------------------------------------

    chars = [" "] * WIDTH

    for position, weekday in zip(
        POSITIONS,
        WEEKDAYS,
    ):
        start = position - 1

        for offset, char in enumerate(
            weekday
        ):
            index = start + offset

            if 0 <= index < WIDTH:
                chars[index] = char

    header = "".join(chars).rstrip()

    if use_color:
        output.append(
            f"\033[38;2;255;255;255m"
            f"{header}"
            f"{RESET}"
        )
        output.append("")
    else:
        output.append(header)

    # ------------------------------------------------------
    # Rows
    # ------------------------------------------------------

    for row in ROWS:

        # No separate key column anymore.
        parts: list[str] = []

        visible_position = 0

        for position, record in zip(
            POSITIONS,
            records,
        ):
            cell = _cell(
                row,
                record,
                use_color,
            )

            # Remove ANSI sequences only for width calculation.
            plain_cell = re.sub(
                r"\x1b\[[0-9;]*m",
                "",
                cell,
            )

            cell_width = len(
                plain_cell
            )

            # Keep your current cell offset:
            # one terminal position left of weekday center.
            start = (
                position
                - (cell_width // 2)
                - 1
            )

            spaces = (
                start
                - visible_position
            )

            if spaces > 0:
                parts.append(
                    " " * spaces
                )

            parts.append(cell)

            visible_position = (
                start
                + cell_width
            )

        output.append(
            "".join(parts)
        )

    return "\n".join(output)


# ==========================================================
# PUBLIC ENTRY POINT
# ==========================================================

def run(
    week_lines: Sequence[str],
    reference_day: dt.date,
    *,
    stream: TextIO | None = None,
    use_color: bool | None = None,
) -> str:
    """Render and print the weekly tracker."""

    output_stream = (
        stream
        if stream is not None
        else sys.stdout
    )

    if use_color is None:
        is_tty = getattr(
            output_stream,
            "isatty",
            None,
        )

        use_color = bool(
            is_tty
            and is_tty()
        )

    rendered = render(
        week_lines,
        reference_day,
        use_color=use_color,
    )

    print(
        rendered,
        file=output_stream,
    )

    # Two empty lines after complete tracker.
    print("", file=output_stream)
    print("", file=output_stream)

    return rendered


__all__ = [
    "run",
    "render",
    "parse_day",
]
