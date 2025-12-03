#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"
SERVICE_NAME="$(basename "$SCRIPT_DIR")"

# --- Vorbedingungen ---
if [ ! -f "$SCRIPT_DIR/config.ini" ]; then
  echo "config.ini file not found. Please make sure it exists. If not created yet, please copy it from config.example."
  exit 1
fi

# --- Logs aufräumen ---
rm -f "$SCRIPT_DIR"/current.log*

# --- Rechte setzen ---
chmod 0755 "$SCRIPT_DIR/install.sh"
chmod 0755 "$SCRIPT_DIR/restart.sh"
chmod 0755 "$SCRIPT_DIR/uninstall.sh"
chmod 0755 "$SCRIPT_DIR/service/run"
chmod 0755 "$SCRIPT_DIR/service/log/run"
chmod 0755 "$SCRIPT_DIR/dbus-growatt-shinex.py"

# --- Symlink setzen ---
mkdir -p /service
ln -sfn "$SCRIPT_DIR/service" "/service/$SERVICE_NAME"

# --- rc.local vorbereiten ---
filename="/data/rc.local"
if [ ! -f "$filename" ]; then
  printf '%s\n' '#!/bin/bash' > "$filename"
  chmod 0755 "$filename"
fi

# --- Helferfunktion: exakt eine Zeile sicherstellen + leere Zeilen entfernen ---
ensure_single_line() {
  local file="$1"
  local line="$2"
  local tmp
  tmp="$(mktemp)"

  awk -v l="$line" '
    # Leerzeilen überspringen
    NF == 0 { next }
    # Zeile suchen und nur einmal behalten
    $0 == l { if (++n == 1) print; next }
    # Rest normal ausgeben
    { print }
    END {
      if (n == 0) print l
    }
  ' "$file" > "$tmp"

  # Rechte & Eigentümer übernehmen
  chown --reference="$file" "$tmp" 2>/dev/null || true
  chmod --reference="$file" "$tmp" 2>/dev/null || true
  mv "$tmp" "$file"
}

# --- rc.local: Eintrag bereinigen und sichern ---
ensure_single_line "$filename" "/bin/bash $SCRIPT_DIR/install.sh"

if [ $(stat -c "%a" "$filename") -ne 755 ]; then
  chmod 0755 $filename
fi

# --- service/log/run: multilog-Zeile bereinigen und sichern ---
logrun="$SCRIPT_DIR/service/log/run"
if [ ! -f "$logrun" ]; then
  mkdir -p "$SCRIPT_DIR/service/log"
  : > "$logrun"
  chmod 755 "$logrun"
fi
ensure_single_line "$logrun" "exec multilog t s153600 n2 /var/log/$SERVICE_NAME"
