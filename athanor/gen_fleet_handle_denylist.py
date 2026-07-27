#!/usr/bin/env python3
"""ATH-3397: generate the fork-local fleet-handle denylist from the roster SSOT.

The export-safety gate must block internal fleet-agent handles from appearing
in published customer artifacts on the public forks. asabi's ruling on this
class: do NOT hardcode the handle list -- it goes stale the moment the
fleet gains a member and then reads as coverage while missing the new name.
Consume the canonical roster SSOT instead: athanor-builder's
``tools/agent-handoff/roles.json`` (ATH-1343), so a new member's display name
appears in the gate automatically.

The forks cannot import athanor-builder, so this generator runs at FLEET level
(where roles.json is readable) and commits a derived denylist into the fork.
Integrity of the committed copy is enforced fork-locally by a stamp; freshness
against the live roster is enforced by re-running this generator on any roster
change (fleet-level), because a hash proves bytes are unchanged, never current.

DERIVATION -- the catch that keeps the gate usable: roles.json mixes person
HANDLES (the human display names) with generic ROLE-KEYS (research, builder,
platform, qa, cto, gpu, dogfood). Banning the role-keys would red on ordinary
English -- "builder" and "research" appear
all over upstream RTL -- so the gate would be disabled within a day. We select
person-handles only by excluding the generic role-key set. A new person handle
still auto-appears; a new generic role-key correctly does not get denied.

Usage:
  python3 athanor/gen_fleet_handle_denylist.py --roles <path/to/roles.json> \
      --out athanor/fleet_handle_denylist.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Generic role-keys / function-words in the roster that are NOT person-handles.
# Denying these would fire on ordinary English (upstream RTL says "builder"/
# "research" constantly). This is the small, stable exclusion set; everything
# else in the roster is treated as a person-handle so new members auto-appear.
# (This file holds NO verbatim person-handle -- the handles come from roles.json
# at generation time -- so the export-safety gate does not self-flag on it.)
GENERIC_ROLE_TERMS: frozenset[str] = frozenset(
    {
        "cto", "platform", "research", "qa", "builder",
        "gpu", "gpu-agent", "gpu-research", "qa-agent",
        "orchestrator", "dogfood",
        # generic role-word in the non-agent map ("company founder" is ordinary
        # English); the founder PERSON-handles are included via the union.
        "founder",
    }
)


# Founder/staff ALT-handles (Bob's find, asabi ruling 2026-07-27): a denylist of
# canonical names does nothing about an alternate handle -- "ai"+"dan" being
# denied does not catch "aidan"+"by". These exist in NO machine-readable identity
# source today; ATH-3427's roster will own alt-names, and this constant is the
# documented stopgap that dies when it does. Fragment-built (same self-flag
# discipline as everything else here).
KNOWN_ALT_HANDLES: tuple[str, ...] = (
    "aidan" + "by",
    "hongsk" + "sam",
)


def extract_non_agent_names(slack_post_source: str) -> list[str]:
    """Person-name keys of ``_NON_AGENT_ROLES`` in the slack_post source.

    ATH-3426 finding 2: roles.json is NOT the only internal identity list —
    slack_post carries ``_NON_AGENT_ROLES`` (founders, customer contacts, and
    new teammates registered there by builder #939). A denylist derived from
    roles.json alone misses those person-handles, so a public packet crediting
    one of them would pass the gate. asabi ruling 2026-07-27: union BOTH
    sources here (the stopgap); the durable fix is one identity SSOT with a
    kind field, tracked separately (Bob's).

    Parsed via ast (never imported) so the generator has no side effects and
    needs no importable path for a script without a .py extension.
    """
    import ast as _ast

    tree = _ast.parse(slack_post_source)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "_NON_AGENT_ROLES":
                    if not isinstance(node.value, _ast.Dict):
                        raise ValueError("_NON_AGENT_ROLES is not a dict literal")
                    return sorted(
                        k.value.lower()
                        for k in node.value.keys
                        if isinstance(k, _ast.Constant) and isinstance(k.value, str)
                    )
    raise ValueError("_NON_AGENT_ROLES not found in the given slack_post source")


def derive_handles(roles: dict, extra_names: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Person-handles from the roster (role keys + rename aliases +
    bot_display_names) UNION any extra person-name sources (the
    ``_NON_AGENT_ROLES`` names), minus the generic role-key terms.
    Sorted, lowercased."""
    names: set[str] = set(extra_names)
    names.update(KNOWN_ALT_HANDLES)
    for key in roles.get("roles", {}):
        names.add(key)
    for alias in roles.get("_renames", {}):
        if not alias.startswith("_"):
            names.add(alias)
    for role in roles.get("roles", {}).values():
        if isinstance(role, dict) and role.get("bot_display_name"):
            names.add(role["bot_display_name"])
    handles = {n.lower() for n in names if n.lower() not in GENERIC_ROLE_TERMS}
    return sorted(handles)


def stamp_for(handles: list[str]) -> str:
    """Integrity stamp: sha256 over the sorted handle list. A hand-edit of the
    committed denylist that does not also update the stamp is detected at
    gate-run time (fork-local). Proves integrity only -- NOT freshness."""
    return hashlib.sha256("\n".join(sorted(handles)).encode()).hexdigest()


def build(roles: dict, extra_names: list[str] | tuple[str, ...] = ()) -> dict:
    handles = derive_handles(roles, extra_names)
    return {
        "_doc": (
            "Fleet-agent handles that must not appear in published customer "
            "artifacts on this public fork (ATH-3397). GENERATED from the roster "
            "SSOT roles.json (ATH-1343) by athanor/gen_fleet_handle_denylist.py "
            "-- do not hand-edit; regenerate. The gate verifies `stamp` against "
            "`handles` on every run (integrity); freshness vs the live roster is "
            "a fleet-level re-generation obligation."
        ),
        "source": "athanor-builder tools/agent-handoff/roles.json (person-handles only)",
        "handles": handles,
        "stamp": stamp_for(handles),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the fork fleet-handle denylist from roles.json")
    ap.add_argument("--roles", required=True, help="path to the canonical roles.json roster")
    ap.add_argument(
        "--non-agent",
        default=None,
        help="path to the slack_post script; its _NON_AGENT_ROLES person-names "
        "are unioned in (ATH-3426 finding 2 — roles.json alone misses them)",
    )
    ap.add_argument("--out", required=True, help="output denylist json path")
    args = ap.parse_args(argv)
    roles = json.loads(Path(args.roles).read_text())
    extra: list[str] = []
    if args.non_agent:
        extra = extract_non_agent_names(Path(args.non_agent).read_text())
    payload = build(roles, extra)
    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {args.out}: {len(payload['handles'])} handles, stamp {payload['stamp'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
