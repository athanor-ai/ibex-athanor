#!/usr/bin/env bash
set -euo pipefail
: "${YOSYS:?Set YOSYS to the pinned Yosys 0.66+181 binary}"
$YOSYS -s replay_equiv_yosys66.ys > logs/equiv_yosys66.replay.log
