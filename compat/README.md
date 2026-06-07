# Release capability descriptors

Each `*.json` here describes the rule-evaluation vocabulary of a **supported
released Trustabl binary**. The `compat-gate` CI job (`tools/check_rule_compat.py`)
uses them to fail a PR that would crash a deployed binary — e.g. a rule in a
`language` an older binary doesn't recognize and hard-fails on.

## Why this exists

A deployed binary pulls these rules at scan time. If a rule uses a vocabulary
value the binary can't evaluate in a dimension it isn't forward-compatible about,
that binary hard-fails its **entire** rule load and can't scan at all. v0.1.3
broke exactly this way on `language: csharp/php/rust`. The gate shifts that check
left: it's a red X on the rules PR instead of a production incident.

## Adding a descriptor when a release ships

Newer engines emit their own descriptor:

```
trustabl capabilities > compat/v0.1.4.json
```

A fully forward-compatible build reports `"hard_fail_dimensions": []` — it skips
rules it can't evaluate rather than crashing, so it constrains nothing here.

`v0.1.3.json` is hand-authored because v0.1.3 predates the `capabilities`
command; it lists `["language"]` as its one hard-fail dimension.

## Retiring a descriptor

Delete a descriptor when that release is no longer supported. Once every
remaining descriptor reports `hard_fail_dimensions: []`, the gate can never fail
— at which point new-language rules are safe to merge.
