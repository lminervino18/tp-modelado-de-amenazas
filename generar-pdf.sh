#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTML="$SCRIPT_DIR/informe.html"
OUTPUT="$SCRIPT_DIR/informe_temp.pdf"

echo "Generando PDF..."

google-chrome \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="$OUTPUT" \
  --print-to-pdf-no-header \
  "file://$HTML" 2>/dev/null

echo "Listo: $OUTPUT"
