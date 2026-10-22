#!/bin/sh
set -eu
cd "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
helm_bin=${HELM_BIN:-helm}
command -v "$helm_bin" >/dev/null 2>&1 || { echo "Helm is required (or set HELM_BIN)." >&2; exit 1; }
python3 -c 'import yaml' || { echo "Install requirements-dev.txt first." >&2; exit 1; }
for values in examples/faostat.yaml examples/tiva.yaml; do
  "$helm_bin" lint charts/ontop --strict -f "$values"
done
HELM_BIN="$helm_bin" python3 -m unittest discover -s tests -p 'test_*.py' -v
