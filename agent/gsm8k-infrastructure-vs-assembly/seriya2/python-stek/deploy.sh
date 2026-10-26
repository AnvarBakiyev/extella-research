#!/bin/sh
# deploy.sh <новый steps_handler.py> <cases.json>: проверить кандидата и только тогда переключить ~/pystek/current
set -e; NEW="$1"; CASES="$2"; PY="${PY:-python3}"
SHA=$(shasum -a 256 "$NEW" 2>/dev/null | cut -c1-12 || sha256sum "$NEW" | cut -c1-12)
"$PY" "$(dirname "$0")/check_release.py" "$NEW" "$CASES" || { echo "отказ: кандидат $SHA меняет исходы, не установлен"; exit 1; }
mkdir -p ~/pystek/releases/$SHA && cp "$NEW" ~/pystek/releases/$SHA/steps_handler.py && ln -sfn ~/pystek/releases/$SHA ~/pystek/current
echo "установлен $SHA на $(hostname)"
