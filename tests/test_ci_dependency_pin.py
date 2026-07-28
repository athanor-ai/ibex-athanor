"""CI must install pytest at ONE exactly-pinned version (ATH-3443 class).

A test result is a property of (TREE x RESOLVED DEPENDENCIES). An unpinned
install makes a green unreproducible -- the one thing a green is supposed to
be -- and this fork's results are cited in receipts for published, hash-bound,
PUBLIC evidence. `main` on athanor-kairos went red with no code change when
`mcp 2.0.0` published against an uncapped `mcp>=1.0`; this install site
had no bound of any kind.

The pin is EXACT rather than a ceiling: "reproducible within a major" is not
reproducible, and evidence needs the stronger property.

The pin is DEFINED ONCE and referenced by every site. There is currently only ONE install site here. The single definition is not
for today's count -- it is so that adding a second site cannot introduce a
second version string, which is how the openc910 twin ended up with five
copies to keep in step. These tests make that divergence UNCONSTRUCTIBLE.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is present in CI and locally
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "export-safety.yml"

# The single definition every install site must reference.
_PIN_VAR = "PYTEST_PIN"
# An install of pytest that does NOT go through the pin variable.
_UNPINNED = re.compile(r"pip\s+install\b(?![^\n]*\$\{?" + _PIN_VAR + r")[^\n]*\bpytest\b")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_the_pin_is_defined_exactly_once_and_is_exact():
    """ONE definition, and `==` rather than `<` or `>=`.

    BOTH SPELLINGS COUNT. The first version matched only the YAML `KEY: value`
    form, so a SHELL assignment inside a `run:` block was invisible to it:

        PYTEST_PIN="pytest==8.0.0"
        python3 -m pip install --quiet "$PYTEST_PIN"

    That shadows the workflow env for that step, installs an entirely
    different version, and satisfies the anti-drift test below because the
    line does reference the variable. Four tests green, pytest 8.0.0
    installed. (bob, openc910 #87, executed.)

    A definition counter that knows one of the two ways to define the thing is
    a presence check wearing a stronger name.
    """
    text = _workflow_text()
    yaml_defs = re.findall(rf"^\s*{_PIN_VAR}\s*:\s*(.+)$", text, re.M)
    shell_defs = re.findall(rf"^\s*(?:export\s+)?{_PIN_VAR}=(.+)$", text, re.M)
    definitions = yaml_defs + shell_defs
    assert len(definitions) == 1, (
        f"expected exactly one {_PIN_VAR} definition, found {len(definitions)} "
        f"({len(yaml_defs)} YAML, {len(shell_defs)} shell): {definitions}. "
        f"Two definitions is two versions waiting to diverge -- and a shell "
        f"assignment in a run block silently shadows the workflow env."
    )
    value = definitions[0].strip().strip('"').strip("'")
    assert re.fullmatch(r"pytest==\d+(\.\d+)*", value), (
        f"the pin must be EXACT, got {value!r}. A ceiling gives 'reproducible "
        f"within a major'; receipts citing this fork need reproducible."
    )


def test_no_install_site_bypasses_the_pin():
    """THE ANTI-DRIFT CONTRACT. This is what makes miss-one unconstructible.

    Any `pip install ... pytest` that does not route through the pin variable
    is a site that will float, and it would look identical to a pinned one in
    review.
    """
    text = _workflow_text()
    offenders = [
        line.strip()
        for line in text.splitlines()
        if _UNPINNED.search(line)
    ]
    assert not offenders, (
        "these install sites bypass the single pin and will resolve freshly "
        f"every run: {offenders}"
    )


def test_every_pytest_install_actually_references_the_pin():
    """NECESSITY, from the other direction.

    The test above forbids unpinned installs. It would also pass on a workflow
    with NO pytest installs at all -- vacuous if the steps were ever removed or
    renamed. This one asserts the sites exist and all of them use the variable,
    so the pair pins both directions.
    """
    text = _workflow_text()
    installs = [ln.strip() for ln in text.splitlines() if re.search(r"pip\s+install", ln)]
    assert installs, "no pip install sites found; this suite would be vacuous"
    using_pin = [ln for ln in installs if _PIN_VAR in ln]
    assert len(using_pin) == len(installs), (
        f"{len(installs) - len(using_pin)} of {len(installs)} install sites do "
        f"not reference {_PIN_VAR}: {[l for l in installs if _PIN_VAR not in l]}"
    )


@pytest.mark.skipif(yaml is None, reason="pyyaml not available")
def test_the_pin_is_visible_to_every_job_via_workflow_level_env():
    """POSITION, not just presence. A pin defined inside one job's `env:` is
    invisible to the others -- the variable would expand to empty and the
    install would silently fall back to unpinned pytest, which is the failure
    mode this whole file exists to prevent."""
    data = yaml.safe_load(_workflow_text())
    env = data.get("env") or {}
    assert _PIN_VAR in env, (
        f"{_PIN_VAR} is not defined at WORKFLOW level; a job-scoped definition "
        f"expands to empty in every other job and installs float silently. "
        f"Found workflow env: {sorted(env)}"
    )
