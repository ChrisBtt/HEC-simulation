#!/usr/bin/env bash
set -Eeuo pipefail

# Find Python executable
PYTHON_CMD=$(which python3 2>/dev/null || which python 2>/dev/null || command -v python3 2>/dev/null || echo "")
if [[ -z "$PYTHON_CMD" ]]; then
  # Try common Python installation locations on Windows
  for python_path in \
    "C:/Python313/python" \
    "C:/Python312/python" \
    "E:/Christoph/Programs/Python/Python313/python" \
    "/c/Python313/python" \
    "/c/Python312/python"; do
    if [[ -f "$python_path" ]] || [[ -f "${python_path}.exe" ]]; then
      PYTHON_CMD="$python_path"
      break
    fi
  done
fi

if [[ -z "$PYTHON_CMD" ]]; then
  echo "ERROR: Python not found. Please ensure Python is installed and in PATH."
  exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Project root: adjust this if needed, or leave as the current directory.
PROJECT_ROOT="$(pwd)"

YAML_FILE="$PROJECT_ROOT/config/dataset_3dct.yaml"
TOPAS_DIR="$PROJECT_ROOT/TOPAS_simulation_data/dataset_3dct"
RESULTS_DIR="$TOPAS_DIR/results"
PATHS_FILE="$PROJECT_ROOT/config/paths.txt"

if [[ ! -f "$PATHS_FILE" ]]; then
  echo "ERROR: Datei nicht gefunden: $PATHS_FILE"
  exit 1
fi

CT_PATHS=()
while IFS= read -r line; do
  # Remove carriage returns and trim whitespace
  line="${line//$'\r'/}"
  line="$(echo "$line" | xargs)"
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  CT_PATHS+=("$line")
done < "$PATHS_FILE"

# -----------------------------------------------------------------------------
# Backup original YAML and restore it automatically on exit
# -----------------------------------------------------------------------------

TMP_BACKUP="$(mktemp)"
cp "$YAML_FILE" "$TMP_BACKUP"

cleanup() {
  cp "$TMP_BACKUP" "$YAML_FILE"
  rm -f "$TMP_BACKUP"
}
trap cleanup EXIT

# -----------------------------------------------------------------------------
# Helper: update patient.dicom_directories in YAML
# -----------------------------------------------------------------------------

update_yaml_ct_path() {
  local ct_path="$1"

  "$PYTHON_CMD" - "$YAML_FILE" "$ct_path" <<'PY'
import re
import sys
from pathlib import Path

yaml_file = Path(sys.argv[1])
ct_path = sys.argv[2]

text = yaml_file.read_text()

pattern = r'(^  dicom_directories:\n)(?:^(?:\s*#.*|\s*-\s*.*)\n)*(?=^  parameters:\n)'
replacement = r'\1    - ' + ct_path + '\n'

new_text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)

if n != 1:
    raise SystemExit("ERROR: Could not uniquely replace 'dicom_directories' block in YAML.")

yaml_file.write_text(new_text)
PY
}

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

mkdir -p "$RESULTS_DIR"

for ct_path in "${CT_PATHS[@]}"; do
  echo "============================================================"
  echo "Processing CT:"
  echo "  $ct_path"
  echo "============================================================"

  if [[ ! -d $ct_path ]]; then
    echo "WARNING: CT directory does not exist, skipping:"
    echo "  $ct_path"
    continue
  fi

  echo "[1/5] Updating YAML ..."
  update_yaml_ct_path "$ct_path"

  echo "[2/5] Running hecTool ..."
  (
    cd "$PROJECT_ROOT"
    printf 'y\n' | "$PYTHON_CMD" -m hecTool config/dataset_3dct.yaml --threadcount 24
  )

  echo "[3/5] Running TOPAS ..."
  (
    cd "$TOPAS_DIR"
    topas simulation.txt > topas_log.txt
  )

  echo "[4/5] Creating target result directory ..."
  # Mirror the input path under results/, but strip the leading slash
  rel_ct_path="${ct_path#/}"
  target_dir="$RESULTS_DIR/$rel_ct_path"
  mkdir -p "$target_dir"

  echo "[5/5] Moving CSV results ..."
  shopt -s nullglob
  csv_files=("$RESULTS_DIR"/*.csv)
  if (( ${#csv_files[@]} == 0 )); then
    echo "WARNING: No CSV files found in $RESULTS_DIR"
  else
    mv "${csv_files[@]}" "$target_dir/"
    echo "Moved ${#csv_files[@]} CSV file(s) to:"
    echo "  $target_dir"
  fi
  shopt -u nullglob

  echo "Done for:"
  echo "  $ct_path"
  echo
done

echo "All CTs processed."