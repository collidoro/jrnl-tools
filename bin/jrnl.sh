#!/usr/bin/env bash
# --------------------------------------------------
# --- JRNL WRAPPER (weekly agenda, bash version) ---
# --------------------------------------------------

REAL_JRNL="$HOME/.local/venvs/jrnl/bin/jrnl"

JRNl_VAULT="$HOME/Vaults/Mariano"
AGENDA_DIR="$JRNl_VAULT/02-Agenda"
JOURNAL_FILE="$JRNl_VAULT/03-Notes/Jrnl/jrnl.md"
JRNL_HELP="$HOME/.config/jrnl-help.txt"

AGENDA_BIN="$HOME/.local/bin/jrnl-agenda"

jrnl() {
  if (( $# == 0 )); then
    "$REAL_JRNL" -n 1000 2>&1 | awk '

    # --------------------------------------------------
    # Einen kompletten jrnl-Eintrag ausgeben
    # --------------------------------------------------
    function flush_entry(    indent, avail, cut, line) {
        if (!have_entry)
            return

        indent = length(entry_base) + length(entry_tag)
        avail = 50 - indent

        while (length(entry_body) > avail) {
            cut = avail

            while (cut > 1 && substr(entry_body, cut, 1) != " ")
                cut--

            if (cut == 1)
                cut = avail

            line = substr(entry_body, 1, cut)
            sub(/[[:space:]]+$/, "", line)

            if (first_line) {
                printf "%s%s%s\n", entry_base, entry_tag, line
                first_line = 0
            } else {
                printf "%*s%s\n", indent, "", line
            }

            entry_body = substr(entry_body, cut + 1)
            sub(/^[[:space:]]+/, "", entry_body)
        }

        if (entry_body != "") {
            if (first_line)
                printf "%s%s%s\n", entry_base, entry_tag, entry_body
            else
                printf "%*s%s\n", indent, "", entry_body
        }

        have_entry = 0
        entry_base = ""
        entry_tag = ""
        entry_body = ""
        first_line = 1
    }


    # --------------------------------------------------
    # ANSI-Codes für Erkennung entfernen
    # --------------------------------------------------
    {
        clean = $0
        gsub(/\033\[[0-9;]*m/, "", clean)
    }


    # --------------------------------------------------
    # jrnl Titelbox -> eigene Highlight-Leiste
    # --------------------------------------------------
    /entries found/ {
        flush_entry()

        line = clean
        gsub(/[┃┏┓┗┛━]/, "", line)
        sub(/^[[:space:]]+/, "", line)
        sub(/[[:space:]]+$/, "", line)
        sub(/entries found/, "Einträge gefunden", line)
        
	printf "\n\033[7m%-50s\033[0m\n\n", line
        next
    }


    # Rahmen oben/unten ausblenden
    clean ~ /^[[:space:]]*[┏┗].*[┓┛][[:space:]]*$/ {
        next
    }


    # --------------------------------------------------
    # Beginn eines neuen jrnl-Eintrags
    # --------------------------------------------------
    /^[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} / {
        flush_entry()

        date = $1
        time = $2

        $1 = ""
        $2 = ""
        sub(/^[[:space:]]+/, "", $0)

        gsub(/-/, "", date)

        text = $0

        entry_base = date " " time "  "
        entry_tag = ""
        entry_body = text

        if (match(entry_body, /^@[A-Za-z0-9_-]+[[:space:]]+/)) {
            entry_tag = substr(entry_body, 1, RLENGTH)
            entry_body = substr(entry_body, RLENGTH + 1)
        }

        have_entry = 1
        first_line = 1
        next
    }


    # --------------------------------------------------
    # Bereits von Core-jrnl umgebrochene Folgezeilen
    # wieder mit dem Eintrag zusammensetzen
    # --------------------------------------------------
    {
        if ($0 != "") {
            line = $0
            sub(/^[[:space:]]+/, "", line)

            if (have_entry) {
                if (entry_body != "")
                    entry_body = entry_body " " line
                else
                    entry_body = line
            }

            next
        }


        # Leerzeile beendet den aktuellen Eintrag
        flush_entry()
        print ""
    }


    END {
        flush_entry()
    }
    '

    return
  fi

  local subcmd="$1"
  shift

  # --------------------------------------------------
  # help
  # --------------------------------------------------
  if [ "$subcmd" = "help" ]; then
    if [ -f "$JRNL_HELP" ]; then
      cat "$JRNL_HELP"
    else
      echo "jrnl help file missing: $JRNL_HELP" >&2
    fi
    return 0
  fi

  # --------------------------------------------------
  # bind
  # --------------------------------------------------
  if [ "$subcmd" = "bind" ]; then
    local f="$HOME/.config/jrnl-bind.txt"

    if [ "$1" = "--edit" ]; then
      ${EDITOR:-vi} "$f"
    else
      if [ -f "$f" ]; then
        cat "$f"
      else
        echo "jrnl bind file missing: $f" >&2
      fi
    fi

    return $?
  fi

  # --------------------------------------------------
  # YYMMDD (anzeigen / editieren / schreiben)
  # --------------------------------------------------
  if [[ "$subcmd" =~ ^[0-9]{6}$ ]]; then
    local code="$subcmd"

    if [ "$1" = "--edit" ]; then
      "$AGENDA_BIN" "$code" --edit
      return $?
    fi

    case "$1" in
      e|f|t|-|l|r|x)
        local mode="$1"
        shift
        "$AGENDA_BIN" "$code" "$mode" "$@"
        return $?
        ;;
    esac

    "$AGENDA_BIN" "$code"
    return $?
  fi

  # --------------------------------------------------
  # Agenda Shortcuts (heute)
  # --------------------------------------------------
  case "$subcmd" in
    e|f|t|-|l|r|x)
      "$AGENDA_BIN" "$subcmd" "$@"
      return $?
      ;;

    today|show)
      if [ "$1" = "--edit" ]; then
        "$AGENDA_BIN" today --edit
      else
        "$AGENDA_BIN" today
      fi
      return $?
      ;;

    play)
      "$AGENDA_BIN" play
      return $?
      ;;

    week)
      if [ "$1" = "--edit" ]; then
        "$AGENDA_BIN" week --edit
      else
        "$AGENDA_BIN" week "$@"
      fi
      return $?
      ;;

    # --------------------------------------------------
    # Projekte (unverändert)
    # --------------------------------------------------
    p)
      if [ "$1" = "--delete" ]; then
        local idx="$2"

        if [ -z "$idx" ]; then
          echo "Usage: jrnl p --delete <nr>" >&2
          return 1
        fi

        local line ts

        line="$(grep '@p_' "$JOURNAL_FILE" | sed -n "${idx}p")" || {
          echo "Kein Eintrag mit Nummer $idx gefunden." >&2
          return 1
        }

        ts="$(echo "$line" | awk '{print $1, $2}')"
        "$REAL_JRNL" -on "$ts" --delete
      else
        grep '@p_' "$JOURNAL_FILE" | nl -ba
      fi

      return $?
      ;;

    P)
      grep -roh '@p_[A-Za-z0-9_-]*' "$JRNl_VAULT/03-Notes/Jrnl/" | sort -u
      return $?
      ;;
  esac

  # --------------------------------------------------
  # Fallback: echtes jrnl
  # --------------------------------------------------
  "$REAL_JRNL" "$subcmd" "$@"
}

# optional: direkt aufrufbar
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  jrnl "$@"
fi
