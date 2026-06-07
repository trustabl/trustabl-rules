#!/usr/bin/env python3
"""Compatibility gate for the trustabl-rules pack.

The deployed Trustabl binary pulls these rules at scan time. An older binary
hard-fails its ENTIRE rule load if a rule uses a vocabulary value it does not
understand in a dimension it is not forward-compatible about — which is exactly
how the v0.1.3 binary broke when csharp/php/rust rules were merged (it crashes on
an unknown `language`).

This gate prevents that class of break BEFORE merge. For every supported release
descriptor under compat/*.json, and for every dimension that release HARD-FAILS
on (its `hard_fail_dimensions`), it checks that no rule uses an out-of-vocabulary
value in that dimension. A violation fails the PR with the offending rule and
release named.

Release descriptors:
  - compat/v0.1.3.json is hand-authored (v0.1.3 predates the descriptor command).
  - Newer releases publish theirs via `trustabl capabilities > compat/<tag>.json`;
    a fully forward-compatible build reports hard_fail_dimensions: [] and so
    constrains nothing here (it skips, never crashes).

Dependencies: PyYAML.
"""

import glob
import json
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMBINATORS = {"all", "any", "not", "always"}
MAX_DEPTH = 12


def match_predicate_keys(match, depth=0):
    """Top-level predicate keys in a match tree, recursing only through the
    all/any/not combinators — mirroring the engine's forward-compat walk, which
    does NOT descend into a known predicate's nested struct keys."""
    keys = set()
    if not isinstance(match, dict) or depth > MAX_DEPTH:
        return keys
    for key, val in match.items():
        if key in COMBINATORS:
            if key in ("all", "any") and isinstance(val, list):
                for el in val:
                    keys |= match_predicate_keys(el, depth + 1)
            elif key == "not" and isinstance(val, dict):
                keys |= match_predicate_keys(val, depth + 1)
        else:
            keys.add(key)
    return keys


def rule_values(dim, rule, policy):
    """The set of values a rule uses in a given vocabulary dimension."""
    if dim == "language":
        return {rule.get("language") or "python"}  # empty/absent defaults to python
    if dim == "scope":
        return {rule["scope"]} if rule.get("scope") else set()
    if dim == "category":
        return {policy["category"]} if policy.get("category") else set()
    if dim == "applies_to":
        return set(rule.get("applies_to") or [])
    if dim == "predicate":
        return match_predicate_keys(rule.get("match", {}))
    return set()


def descriptor_vocab(desc, dim):
    """The set of values a release descriptor declares for a dimension."""
    if dim == "language":
        return set(desc.get("languages", []))
    if dim == "scope":
        return set(desc.get("scopes", []))
    if dim == "category":
        return set(desc.get("categories", []))
    if dim == "applies_to":
        return {k for kinds in desc.get("applies_to", {}).values() for k in kinds}
    if dim == "predicate":
        return set(desc.get("predicates", []))
    return set()


def load_rules():
    rules = []
    for path in sorted(glob.glob(os.path.join(REPO, "**", "*.yaml"), recursive=True)):
        if os.path.basename(path) == "manifest.yaml" or f"{os.sep}.git{os.sep}" in path:
            continue
        with open(path) as f:
            doc = yaml.safe_load(f)
        if not isinstance(doc, dict):
            continue
        policy = doc.get("policy", {}) or {}
        for rule in doc.get("rules", []) or []:
            rules.append((os.path.relpath(path, REPO), policy, rule))
    return rules


def main():
    descriptors = []
    for path in sorted(glob.glob(os.path.join(REPO, "compat", "*.json"))):
        with open(path) as f:
            descriptors.append(json.load(f))
    if not descriptors:
        print("compat gate: no release descriptors under compat/; nothing to check.")
        return 0

    rules = load_rules()
    failures = []
    for desc in descriptors:
        ver = desc.get("version", "?")
        for dim in desc.get("hard_fail_dimensions", []):
            allowed = descriptor_vocab(desc, dim)
            for relpath, policy, rule in rules:
                used = rule_values(dim, rule, policy)
                bad = sorted(used - allowed)
                if bad:
                    rid = rule.get("id", "?")
                    failures.append(
                        f"{ver}: rule {rid} ({relpath}) uses {dim}={bad}, "
                        f"which {ver} does not recognize and HARD-FAILS on"
                    )

    if failures:
        print("COMPAT GATE FAILED — these rules would crash a deployed binary:\n")
        for line in failures:
            print("  " + line)
        print(
            "\nA binary that hard-fails on an out-of-vocabulary rule cannot scan at all.\n"
            "Hold these rules until the listed releases are out of support, or ship them\n"
            "only once a forward-compatible engine release is the supported floor."
        )
        return 1

    print(
        f"compat gate OK: {len(rules)} rules checked against "
        f"{len(descriptors)} supported release descriptor(s); none would crash."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
