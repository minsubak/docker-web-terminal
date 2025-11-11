#!/usr/bin/env bash
set -euo pipefail
trap 'echo "Caught SIGTERM"; exit 0' TERM INT
# 필요 시 인자 전달: main.py --mode=${MODE:-interactive}
exec "$@"
