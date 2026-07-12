#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
YOSYS=${YOSYS:-yosys}
"$YOSYS" -s replay_equiv_yosys66.ys | tee equiv_yosys66.log
