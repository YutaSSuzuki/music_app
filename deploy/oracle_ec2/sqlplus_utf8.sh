#!/usr/bin/env bash
set -euo pipefail

# SQL files in this repository are UTF-8. Tell SQL*Plus to use Oracle UTF-8.
export NLS_LANG="${NLS_LANG:-.AL32UTF8}"

exec sqlplus "$@"
