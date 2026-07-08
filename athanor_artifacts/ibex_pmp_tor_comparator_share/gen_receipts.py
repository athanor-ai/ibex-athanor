#!/usr/bin/env python3
"""Generate the ibex_pmp TOR-comparator-share tradeoff-row receipts (mirrors
ibex_alu_bwlogic schema). Selected toolchain: yosys_0_66_181 oss-cad-suite."""
import hashlib, json
from pathlib import Path

ROW = Path(__file__).resolve().parent
LIBSHA = "ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9"
TOOLCHAIN = {
    "abc": "yosys-abc bundled with OSS CAD Suite 2026-06-30",
    "oss_cad_suite_release": "2026-06-30",
    "yosys": "Yosys 0.66+181",
    "yosys_git_sha": "afe6b18f2",
}

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def pct(gate, gold):
    return round((gate - gold) / gold * 100, 4)

# --- measured under selected y0.66 toolchain (deterministic) ---
GOLD_AREA, GATE_AREA = 13042.5088, 11410.944
GOLD_MAP, GATE_MAP = 2141, 1933
GOLD_GEN, GATE_GEN = 3583, 2916
GOLD_DELAY, GATE_DELAY = 5.467, 5.515            # OpenSTA max propagation delay, area-oriented
GOLD_TOG, GATE_TOG = 2664, 2664                  # iverilog boundary toggle

A = ROW / "artifacts"
L = ROW / "logs"

def w(name, obj):
    (ROW / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")

# formal_cert.json — single-instrument yosys SAT miter; independent replay pending cross-VM
w("formal_cert.json", {
    "method": "yosys_sat_miter",
    "proved": True,
    "detail": "yosys_sat_miter status pass; combinational two-file equivalence, "
              "all inputs + trigger imported over pmp_req_err_o, no model found (non-vacuous).",
    "independent_verification": {
        "status": "pending_cross_vm",
        "note": "Single-instrument (author box) yosys 0.9 SAT miter: SUCCESS, non-vacuous. "
                "Independent cross-VM replay of the comb-EC bites + area/toggle/propagation-delay "
                "is required before acceptance (Quan/Ronald).",
    },
})

w("area.json", {
    "abc_mapped_cells": {
        "delta_pct": pct(GATE_MAP, GOLD_MAP), "gate_cells": GATE_MAP, "gold_cells": GOLD_MAP,
        "liberty_sha256": LIBSHA,
        "metric_note": "Mapped Sky130 cell count after Yosys 0.66+181 synth, dfflibmap, abc, stat.",
    },
    "generic_cells": {
        "delta_pct": pct(GATE_GEN, GOLD_GEN), "gate_cells": GATE_GEN, "gold_cells": GOLD_GEN,
    },
    "stat_liberty_chip_area": {
        "delta_pct": pct(GATE_AREA, GOLD_AREA), "gate_area": GATE_AREA, "gold_area": GOLD_AREA,
        "liberty_sha256": LIBSHA,
        "metric_note": "Customer-facing area metric, selected Yosys 0.66+181 toolchain.",
    },
})

w("timing.json", {
    "error": None,
    "gate_wns_ns": 0.0, "gate_tns_ns": 0.0, "gold_wns_ns": 0.0, "gold_tns_ns": 0.0,
    "status": "measured_met",
    "sdc_status": "opensta_liberty (opensta_virtual_sdc; source_prep=sv2v_normalized)",
    "timing_note": "All paths meet under a loose 10ns virtual clock; the load-bearing "
                   "metric for this combinational row is max propagation delay "
                   "(toggle_timing_yosys66.json), which regresses.",
})

w("power.json", {
    "compile_file_order": {
        "gate": ["artifacts/ibex_pkg.sv", "artifacts/ibex_pmp_tor_comparator_share.sv"],
        "gold": ["artifacts/ibex_pkg.sv", "artifacts/ibex_pmp.sv"],
    },
    "gate_toggles": GATE_TOG, "gold_toggles": GOLD_TOG,
    "power_method": "iverilog_toggle", "status": "measured_pass",
    "toggle_delta_pct": pct(GATE_TOG, GOLD_TOG), "toggle_source_kind": "sv2v_normalized",
})

w("area_yosys66.json", {
    "abc_mapped_cells": {
        "delta_pct": pct(GATE_MAP, GOLD_MAP), "gate_cells": GATE_MAP, "gold_cells": GOLD_MAP,
        "metric_note": "Final mapped Sky130 cell histogram after Yosys 0.66+181 synth, dfflibmap, abc, stat.",
    },
    "replay_artifact_hashes": {
        "gold_v2001_sha256": sha(A / "ibex_pmp_gold_v2001.v"),
        "gate_v2001_sha256": sha(A / "ibex_pmp_tor_comparator_share_v2001.v"),
        "gold_yosys_area_log_sha256": sha(L / "gold_area_yosys66.log"),
        "gate_yosys_area_log_sha256": sha(L / "gate_area_yosys66.log"),
    },
    "replay_status": {
        "independent_replay_required": True,
        "timing_replay_required": False, "timing_replay_status": "propagation_delay_negative",
        "toggle_replay_required": False, "toggle_replay_status": "flat",
    },
    "stat_liberty_chip_area": {
        "delta_pct": pct(GATE_AREA, GOLD_AREA), "gate_area": GATE_AREA, "gold_area": GOLD_AREA,
        "liberty_sha256": LIBSHA,
        "metric_note": "Current-toolchain area replay is positive (-12.51%). Full-PPA "
                       "customer-facing use is blocked by the Yosys 0.66/OpenSTA "
                       "max-propagation-delay regression in toggle_timing_yosys66.json.",
    },
    "toolchain": TOOLCHAIN,
})

w("toggle_timing_yosys66.json", {
    "propagation_delay": {
        "gold_delay_ns": GOLD_DELAY, "gate_delay_ns": GATE_DELAY,
        "delta_ns": round(GATE_DELAY - GOLD_DELAY, 3),
        "delta_pct": pct(GATE_DELAY, GOLD_DELAY),
        "method": "OpenSTA report_checks -path_delay max over Yosys 0.66+181 + ABC mapped "
                  "netlists with loose virtual clock and zero I/O delay",
        "status": "regression",
        "timing_convention": "combinational_max_propagation_delay",
    },
    "timing": {
        "clock_period_ns": 10.0, "error": None,
        "gate_wns_ns": 0.0, "gate_tns_ns": 0.0, "gold_wns_ns": 0.0, "gold_tns_ns": 0.0,
        "timing_met": True,
        "method": "OpenSTA over Yosys 0.66+181 + ABC mapped netlists, loose virtual clock",
        "sdc_status": "opensta_liberty (opensta_virtual_sdc; source_prep=sv2v_normalized)",
    },
    "toggle": {
        "gate_toggles": GATE_TOG, "gold_toggles": GOLD_TOG,
        "toggle_delta_pct": pct(GATE_TOG, GOLD_TOG),
        "method": "iverilog_toggle on sv2v-normalized RTL", "simulator": "iverilog_toggle",
        "sim_cycles": 200,
    },
    "status": "area_positive_toggle_flat_propagation_delay_negative",
    "toolchain": TOOLCHAIN,
})

# --- manifest: artifacts = 3 source .sv + the 7 JSON receipts ---
artifact_files = [
    "artifacts/ibex_pmp.sv",
    "artifacts/ibex_pmp_tor_comparator_share.sv",
    "artifacts/ibex_pkg.sv",
    "area.json", "area_yosys66.json", "formal_cert.json",
    "power.json", "timing.json", "toggle_timing_yosys66.json",
]
artifacts = {f: {"path": f, "sha256": sha(ROW / f)} for f in sorted(artifact_files)}

w("manifest.json", {
    "schema": "public_frontier_manifest_v1",
    "module": "ibex_pmp",
    "row_contract": "area_tradeoff_yosys66",
    "transform_class": "tor_boundary_comparator_share",
    "status": "formal_pass_yosys66_area_positive_toggle_flat_propagation_delay_negative",
    "toolchain_policy": {
        "customer_status": "customer_area_tradeoff_yosys66",
        "full_ppa_frontier": False,
        "selected_area_receipt": "area_yosys66.json",
        "selected_timing_receipt": "toggle_timing_yosys66.json",
        "selected_toolchain_id": "yosys_0_66_181_oss_cad_suite_2026_06_30",
        "timing_convention": "combinational_max_propagation_delay",
        "tradeoff_note": "Area improves -12.51% and toggle is flat under the selected "
                         "toolchain, but max input-to-output propagation delay regresses "
                         "+0.9% (area-oriented; worse under -fast). Favorable area/timing "
                         "tradeoff, not a full-PPA frontier row.",
    },
    "artifacts": artifacts,
})
print("receipts generated:", sorted(artifact_files) + ["manifest.json"])
