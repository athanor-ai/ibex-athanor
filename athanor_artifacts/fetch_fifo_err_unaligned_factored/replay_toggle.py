#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _sum_tc(path: Path) -> int:
    text = path.read_text()
    return sum(int(value) for value in re.findall(r"\(TC\s+(\d+)\)", text))


gold_toggles = _sum_tc(HERE / "gold.saif")
gate_toggles = _sum_tc(HERE / "gate.saif")
receipt = {
    "method": "saif_tc_sum",
    "gold_toggles": gold_toggles,
    "gate_toggles": gate_toggles,
    "toggle_delta_pct": (gate_toggles - gold_toggles) / gold_toggles * 100 if gold_toggles else None,
    "lead_manifest_toggle_context": json.loads((HERE / "lead_manifest.json").read_text())["toggle"],
}
(HERE / "toggle_proxy.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
