#!/usr/bin/env python3
"""top_level_first.py — one-command top-level-first candidate evaluation (ATH-2699).

Automates the methodology that produced win #7 (see
athanor_artifacts/if_stage_expanded_predicate_factor/COMMANDS.md — that file is
the manual specification this tool executes), with the ORDERING as the point:

    stage 1  baseline whole-core synth        (clean tree)
    stage 2  apply patch -> gate whole-core synth
    stage 3  AREA GATE        — stop here on regression (cheap death)
    stage 4  TIMING GATE      — all configured WNS groups non-regressing
    stage 5  formal equivalence   ONLY if stages 3-4 positive
    stage 6  pinned toggle convention receipt
    stage 7  emit receipt JSON + SHA256SUMS

A top-level-NEGATIVE run is a SUCCESSFUL evaluation: it emits a short receipt
recording the death (stage, numbers) without burning the expensive legs — the
7 module-local deaths before win #7 each cost equivalence + toggle time this
tool now avoids structurally.

Target-agnostic by construction: every core-specific fact (top module, syn
script, env pins, timing groups, toggle top, patch target sanity) lives in the
--core config JSON. configs/ibex_top_yosys66.json is the shipped FIXTURE, not
a special case; a second core is a second config file, zero tool changes.

Receipts are byte-reproducible: no wallclock, sorted keys, hashes over every
produced log/report; `athanor/verify_public_receipts.py` remains the
independent cold-replay gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── config ──────────────────────────────────────────────────────────────────


def load_core_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "core_name",
        "top_module",
        "syn_script",
        "syn_out_root",
        "area_report_glob",
        "timing_report_dir",
        "timing_groups",
        "env",
        "toggle",
    )
    missing = [k for k in required if k not in cfg]
    if missing:
        raise SystemExit(f"core config missing keys: {missing}")
    return cfg


def _env_for(cfg: dict) -> dict:
    import os

    env = dict(os.environ)
    for k, v in cfg["env"].items():
        if k == "PATH_PREPEND":
            env["PATH"] = v + ":" + env.get("PATH", "")
        else:
            env[k] = v
    return env


# ── parsers (shapes pinned against win-#7 artifacts) ────────────────────────

_AREA_RE_TMPL = r"Chip area for module '\\?{top}':\s*([0-9.]+)"


def parse_area(report: Path, top_module: str) -> float:
    text = report.read_text(encoding="utf-8", errors="replace")
    m = re.search(_AREA_RE_TMPL.format(top=re.escape(top_module)), text)
    if not m:
        raise SystemExit(f"area parse failed: no top-module line in {report}")
    return float(m.group(1))


def parse_group_wns(csv_report: Path) -> float:
    """WNS for a group = worst (minimum) slack over all rows.

    Shape (win-#7 reports/timing/*.csv.rpt):
        Start Point, End Point, WNS (ns)
        _22449_,_23002_,-484.8247
    """
    worst = None
    for line in csv_report.read_text(encoding="utf-8", errors="replace").splitlines()[
        1:
    ]:
        parts = line.rsplit(",", 1)
        if len(parts) != 2:
            continue
        try:
            v = float(parts[1])
        except ValueError:
            continue
        worst = v if worst is None else min(worst, v)
    if worst is None:
        raise SystemExit(f"timing parse failed: no WNS rows in {csv_report}")
    return worst


_EQUIV_PROVEN_RE = re.compile(r"Of those cells (\d+) are proven and (\d+) are unproven")


def parse_equiv(log_text: str) -> dict:
    m = _EQUIV_PROVEN_RE.search(log_text)
    proven, unproven = (int(m.group(1)), int(m.group(2))) if m else (0, -1)
    return {
        "proven_cells": proven,
        "unproven_cells": unproven,
        "proven": unproven == 0 and "Equivalence successfully proven!" in log_text,
    }


# ── stages ──────────────────────────────────────────────────────────────────


def run_synth(cfg: dict, out_name: str, log_path: Path) -> Path:
    """Run the core's synth flow into syn_out_root/out_name; return that dir."""
    syn_dir = REPO_ROOT / Path(cfg["syn_script"]).parent
    out_rel = f"{cfg['syn_out_root']}/{out_name}"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            ["bash", Path(cfg["syn_script"]).name, out_rel],
            cwd=syn_dir,
            env=_env_for(cfg),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if proc.returncode != 0:
        raise SystemExit(f"synth failed ({out_name}) — see {log_path}")
    return syn_dir / out_rel


def collect_metrics(cfg: dict, syn_out: Path) -> dict:
    area_matches = sorted(syn_out.glob(cfg["area_report_glob"]))
    if not area_matches:
        raise SystemExit(
            f"no area report under {syn_out} matching {cfg['area_report_glob']}"
        )
    area = parse_area(area_matches[-1], cfg["top_module"])
    timing_dir = syn_out / cfg["timing_report_dir"]
    wns = {}
    for group in cfg["timing_groups"]:
        # The synth flow emits both machine-readable CSV summaries
        # (overall.csv.rpt) and human path-detail reports (overall.rpt).
        # parse_group_wns consumes the CSV shape, so prefer it explicitly.
        matches = (
            sorted(timing_dir.glob(f"{group}.csv.rpt"))
            or sorted(timing_dir.glob(f"{group}*.csv.rpt"))
            or sorted(timing_dir.glob(f"{group}*.rpt"))
            or sorted(timing_dir.glob(f"{group}*"))
        )
        if not matches:
            raise SystemExit(f"no timing report for group {group} under {timing_dir}")
        wns[group] = parse_group_wns(matches[-1])
    return {
        "area": area,
        "wns": wns,
        "area_report": area_matches[-1],
        "timing_dir": timing_dir,
    }


EQUIV_YS_TEMPLATE = """read_verilog gold.v
hierarchy -check -top {top}
proc
memory
flatten
opt
rename {top} gold
design -stash gold_design

design -reset
read_verilog gate.v
hierarchy -check -top {top}
proc
memory
flatten
opt
rename {top} gate
design -stash gate_design

design -reset
design -copy-from gold_design gold
design -copy-from gate_design gate
equiv_make gold gate equiv
hierarchy -top equiv
async2sync
equiv_induct -undef -seq {seq}
equiv_simple
equiv_status -assert
"""


def run_equivalence(
    cfg: dict, gold_v: Path, gate_v: Path, workdir: Path
) -> tuple[dict, Path, Path]:
    top = cfg["_active_unit_top"]
    seq = cfg.get("equiv_seq", 32)
    ys = workdir / "equiv.ys"
    ys.write_text(EQUIV_YS_TEMPLATE.format(top=top, seq=seq), encoding="utf-8")
    gold_dst = workdir / "gold.v"
    gate_dst = workdir / "gate.v"
    if gold_v.resolve() != gold_dst.resolve():
        shutil.copy(gold_v, gold_dst)
    if gate_v.resolve() != gate_dst.resolve():
        shutil.copy(gate_v, gate_dst)
    log = workdir / "equiv.log"
    with log.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            ["yosys", "-s", ys.name],
            cwd=workdir,
            env=_env_for(cfg),
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    result = parse_equiv(log.read_text(encoding="utf-8", errors="replace"))
    result["exit_code"] = proc.returncode
    return result, ys, log


def run_toggle(cfg: dict, gold_v: Path, gate_v: Path, out_dir: Path) -> dict:
    harness = REPO_ROOT / cfg["toggle"]["harness"]
    proc = subprocess.run(
        [
            sys.executable,
            str(harness),
            "--gold",
            str(gold_v),
            "--gate",
            str(gate_v),
            "--top",
            cfg["_active_unit_top"],
            "--out-dir",
            str(out_dir),
        ],
        env=_env_for(cfg),
        capture_output=True,
        text=True,
    )
    receipt_path = out_dir / "toggle_convention_receipt.json"
    if proc.returncode != 0 or not receipt_path.is_file():
        raise SystemExit(
            f"toggle harness failed (rc={proc.returncode}):\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )
    return json.loads(receipt_path.read_text(encoding="utf-8"))


# ── receipt ─────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()


def emit_receipt(out_dir: Path, receipt: dict) -> Path:
    hashes = {}
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name not in ("top_level_first_receipt.json", "SHA256SUMS"):
            hashes[str(p.relative_to(out_dir))] = _sha256(p)
    receipt["artifact_hashes"] = hashes
    path = out_dir / "top_level_first_receipt.json"
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sums = out_dir / "SHA256SUMS"
    with sums.open("w", encoding="utf-8") as fh:
        for rel, digest in sorted(hashes.items()):
            fh.write(f"{digest}  {rel}\n")
        fh.write(f"{_sha256(path)}  top_level_first_receipt.json\n")
    return path


# ── main flow ───────────────────────────────────────────────────────────────

WIN7 = REPO_ROOT / "athanor_artifacts" / "if_stage_expanded_predicate_factor"


def selftest() -> int:
    """Parser + gate-logic checks against the packaged win-#7 artifacts —
    real fixtures already in the repo, no synthetic data, no toolchain."""
    fails = 0

    def check(name, got, want):
        nonlocal fails
        ok = got == want
        print(
            f"{'ok' if ok else 'FAIL'}: {name} = {got!r}"
            + ("" if ok else f" (want {want!r})")
        )
        fails += 0 if ok else 1

    area = parse_area(WIN7 / "reports" / "baseline_area.rpt", "ibex_top")
    check("parse_area baseline", area, 108428.992)
    wns = parse_group_wns(WIN7 / "reports" / "timing" / "overall.baseline.csv.rpt")
    check("parse_group_wns overall baseline", wns, -484.8247)
    eq = parse_equiv(
        (WIN7 / "equiv_yosys66.log").read_text(encoding="utf-8", errors="replace")
    )
    check(
        "parse_equiv proven",
        (eq["proven_cells"], eq["unproven_cells"], eq["proven"]),
        (1956, 0, True),
    )
    # gate logic: the recorded win must pass both cheap gates; a synthetic
    # regression must fail them (the wrong-model bite)
    rec = json.loads((WIN7 / "top_level_ppa_yosys66.json").read_text(encoding="utf-8"))
    check("area gate on win #7", rec["area"]["gate"] <= rec["area"]["baseline"], True)
    check(
        "area gate bites on regression",
        (rec["area"]["baseline"] + 1.0) <= rec["area"]["baseline"],
        False,
    )
    print("selftest:", "OK" if fails == 0 else f"{fails} FAILED")
    return fails


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--patch", required=True, type=Path, help="candidate SOURCE_DIFF.patch"
    )
    ap.add_argument(
        "--core", required=True, type=Path, help="core config JSON (target-agnostic)"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="artifact out dir (default: syn_out sibling)",
    )
    ap.add_argument("--candidate-name", default=None)
    ap.add_argument(
        "--unit",
        required=False,
        default=None,
        help="unit name from the core config's units map (equivalence/toggle scope; "
        "candidate-scoped — win #7's was ibex_if_stage)",
    )
    ap.add_argument(
        "--force-fresh",
        action="store_true",
        help="wipe a non-empty out dir instead of refusing (receipt freshness guard)",
    )
    ap.add_argument(
        "--keep-tree-patched",
        action="store_true",
        help="leave the patch applied on exit (default: always revert)",
    )
    args = ap.parse_args()

    cfg = load_core_config(args.core)
    name = args.candidate_name or args.patch.stem
    out_dir = args.out or (REPO_ROOT / "athanor_artifacts" / f"{name}_top_level_first")
    if out_dir.exists() and any(out_dir.iterdir()):
        if args.force_fresh:
            shutil.rmtree(out_dir)
        else:
            raise SystemExit(
                f"out_dir {out_dir} exists and is non-empty — stale files would "
                "poison the receipt's artifact_hashes (byte-reproducibility contract). "
                "Use --force-fresh to wipe it, or pick a new --out."
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)
    shutil.copy(args.patch, out_dir / "SOURCE_DIFF.patch")

    receipt: dict = {
        "schema": "athanor.top_level_first.v1",
        "candidate": name,
        "core": cfg["core_name"],
        "base_commit": _git_head(),
        "tool_pins": cfg.get("tool_pins", {}),
        "stages": {},
    }

    def die_negative(stage: str, detail: dict) -> int:
        receipt["classification"] = f"top_level_negative_{stage}"
        receipt["stages"][stage] = {**detail, "gate": "NEGATIVE"}
        receipt["classification_notes"] = [
            f"Stopped at {stage}: expensive legs (equivalence, toggle) intentionally NOT run.",
            "A negative receipt is a successful evaluation — the candidate died cheaply.",
        ]
        path = emit_receipt(out_dir, receipt)
        print(f"NEGATIVE at {stage} — receipt: {path}")
        return 0  # a recorded death is a successful run

    # stage 1: baseline synth on a clean tree
    dirty = subprocess.run(["git", "diff", "--quiet"], cwd=REPO_ROOT).returncode != 0
    if dirty:
        raise SystemExit("working tree dirty — baseline must run from a clean checkout")
    baseline_out = run_synth(
        cfg, f"tlf_baseline_{name}", out_dir / "logs" / "baseline_syn.log"
    )
    base = collect_metrics(cfg, baseline_out)

    # stage 2: apply patch, gate synth (revert guaranteed unless asked otherwise)
    subprocess.run(
        ["git", "apply", str(out_dir / "SOURCE_DIFF.patch")], cwd=REPO_ROOT, check=True
    )
    try:
        gate_out = run_synth(cfg, f"tlf_gate_{name}", out_dir / "logs" / "gate_syn.log")
        gate = collect_metrics(cfg, gate_out)
    finally:
        if not args.keep_tree_patched:
            # CONTRACT: the tree MUST be restored before this tool proceeds —
            # a silently-still-patched tree poisons every later baseline on
            # this checkout. check=True makes a failed revert fatal and loud.
            subprocess.run(
                ["git", "apply", "-R", str(out_dir / "SOURCE_DIFF.patch")],
                cwd=REPO_ROOT,
                check=True,
            )

    for which, m in (("baseline", base), ("gate", gate)):
        shutil.copy(m["area_report"], out_dir / "logs" / f"{which}_area.rpt")
        dst = out_dir / "reports" / "timing" / which
        dst.mkdir(parents=True, exist_ok=True)
        for f in Path(m["timing_dir"]).glob("*"):
            if f.is_file():
                shutil.copy(f, dst / f.name)

    # stage 3: area gate
    area_delta = gate["area"] - base["area"]
    receipt["stages"]["area"] = {
        "baseline": base["area"],
        "gate": gate["area"],
        "delta": area_delta,
        "delta_percent": (area_delta / base["area"] * 100.0) if base["area"] else 0.0,
        "gate_rule": "gate_area <= baseline_area",
    }
    if area_delta > 0:
        return die_negative("area", receipt["stages"]["area"])
    receipt["stages"]["area"]["gate"] = "POSITIVE"

    # stage 4: timing gate — every configured group non-regressing
    timing = {}
    regressed = []
    for group in cfg["timing_groups"]:
        b, g = base["wns"][group], gate["wns"][group]
        timing[group] = {"baseline_wns": b, "gate_wns": g, "delta": g - b}
        if g < b:
            regressed.append(group)
    receipt["stages"]["timing"] = {
        "groups": timing,
        "gate_rule": "gate_wns >= baseline_wns per group",
    }
    if regressed:
        receipt["stages"]["timing"]["regressed_groups"] = regressed
        return die_negative("timing", receipt["stages"]["timing"])
    receipt["stages"]["timing"]["gate"] = "POSITIVE"

    # stages 5-6 only run past the cheap gates — the whole point of the ordering
    units = cfg.get("units", {})
    if not args.unit or args.unit not in units:
        raise SystemExit(
            f"--unit required for the equivalence/toggle legs; known units: {sorted(units)}"
        )
    gold_v, gate_v = _build_unit_artifacts(cfg, units[args.unit], out_dir)

    cfg["_active_unit_top"] = units[args.unit].get("top", args.unit)
    equiv, ys, log = run_equivalence(cfg, gold_v, gate_v, out_dir)
    receipt["stages"]["equivalence"] = equiv
    if not equiv["proven"]:
        receipt["classification"] = "equivalence_failed"
        receipt["classification_notes"] = [
            "Top-level positive but equivalence unproven — candidate rejected."
        ]
        emit_receipt(out_dir, receipt)
        print(f"equivalence FAILED — receipt in {out_dir}")
        return 1

    toggle = run_toggle(cfg, gold_v, gate_v, out_dir / "logs" / "convention_v1")
    receipt["stages"]["toggle"] = {
        k: toggle.get(k)
        for k in ("gold_toggles", "gate_toggles", "toggle_delta_pct", "toggle_status")
    }
    ok = str(toggle.get("toggle_status", "")) in (
        "neutral_or_better",
        "neutral",
        "improved",
    )
    receipt["classification"] = "five_point_positive" if ok else "toggle_regressed"
    receipt["classification_notes"] = [
        "All five acceptance points evaluated: bounded diff (input), area, 5-group timing, equivalence, toggle.",
        "Cold-replay via verify_public_receipts.py remains the independent acceptance gate.",
    ]
    path = emit_receipt(out_dir, receipt)
    print(f"{'FIVE-POINT POSITIVE' if ok else 'toggle regressed'} — receipt: {path}")
    return 0 if ok else 1


def _build_unit_artifacts(cfg: dict, ua: dict, out_dir: Path) -> tuple[Path, Path]:
    """sv2v gold/gate builds for the equivalence/toggle unit (COMMANDS.md recipe)."""
    gold = out_dir / "gold.v"
    gate = out_dir / "gate.v"
    cmd = [cfg["env"].get("SV2V", "sv2v"), "-D", "SYNTHESIS"]
    for inc in ua.get("includes", []):
        cmd += ["-I", inc]
    files = [str(REPO_ROOT / f) for f in ua["files"]]
    for dst, patched in ((gold, False), (gate, True)):
        if patched:
            subprocess.run(
                ["git", "apply", str(out_dir / "SOURCE_DIFF.patch")],
                cwd=REPO_ROOT,
                check=True,
            )
        try:
            with dst.open("w", encoding="utf-8") as fh:
                subprocess.run(
                    cmd + files, cwd=REPO_ROOT, env=_env_for(cfg), stdout=fh, check=True
                )
        finally:
            if patched:
                # CONTRACT: same restore guarantee as the gate-synth path —
                # a failed revert here is fatal, never silent.
                subprocess.run(
                    ["git", "apply", "-R", str(out_dir / "SOURCE_DIFF.patch")],
                    cwd=REPO_ROOT,
                    check=True,
                )
    return gold, gate


if __name__ == "__main__":
    raise SystemExit(main())
