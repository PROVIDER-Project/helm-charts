#!/bin/sh
set -eu
cd "$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
./scripts/check.sh
mkdir -p dist
"${HELM_BIN:-helm}" package charts/ontop --destination dist
