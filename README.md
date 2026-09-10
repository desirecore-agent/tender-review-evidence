# tender-evidence-review — Draft v1.2 Publication Package

Independent evidence re-examination skill for the tender review team. **Draft for review — not published, not production-ready.**

## What this skill does

- Re-reads bilateral evidence for every severity finding (tender-side + bid-side)
- Checks negative examples, counter-evidence, and exception clauses
- Verifies calculations with real decimal arithmetic
- Validates image observation records (readability, actual viewing)
- Cross-checks coverage closure by re-counting unique `item_id` end-states
- Refuses to pass incomplete, missing-field, or unsubstantiated claims

## Contract version

This package targets **v1.2** of the team's shared contracts. Authoritative schema directory:

```
<TEAM_ROOT>/shared/contracts/schemas/
```

Six schemas: `project-profile`, `file-manifest`, `requirements`, `coverage`, `findings`, `review-report`.

## v1.2 migration from v1.1

| Area | v1.1 | v1.2 |
|------|------|------|
| `contract_version` | not enforced | required, must equal `v1.2` |
| Validator engine | hand-rolled minimal subset | jsonschema 4.25.1 (`Draft7Validator.check_schema()` + empty `Registry` for remote-block) |
| Schema path | `shared/contracts/` | `shared/contracts/schemas/` |
| Subset / final-admission | `--final-admission` flag, subset default | six-file gate required; `--final-admission` retained as compatibility alias (no behavioral relaxation) |
| Four-state names | `valid_json_null`, `valid_object` | `absent`, `parse_error`, `null`, `object` |
| `manifest_id` binding | not enforced across products | G06: `file-manifest.manifest_id` = `requirements.manifest_id` = `coverage.manifest_id` = `findings.manifest_id` = `review-report.inputs_version.manifest_id`; `project-profile` has no `manifest_id` |

## Quick start

```sh
# ─── 0. Resolve required paths (platform must provide) ─────────────────
# EVIDENCE_SKILL_DIR : absolute path to this skill's root directory.
#   Must not be inside the materials/pack tree or a symlink outside the team.
# PRIVATE_RUNTIME_DIR : per-user per-agent private directory.
#   Must be absolute, writable, and not inside the skill or materials tree.
# BOOTSTRAP_PYTHON : absolute path to a Python >=3.9 interpreter.
#   Used only to create the venv; never installs into system site-packages.

# ─── 1. Guard required variables ──────────────────────────────────────
[ -n "${EVIDENCE_SKILL_DIR:-}" ] && [ -d "$EVIDENCE_SKILL_DIR" ] || { echo "BLOCKED: EVIDENCE_SKILL_DIR not set or not a directory" >&2; exit 2; }
[ -n "${PRIVATE_RUNTIME_DIR:-}" ] && [ -d "$PRIVATE_RUNTIME_DIR" ] || { echo "BLOCKED: PRIVATE_RUNTIME_DIR not set or not a directory" >&2; exit 2; }
[ -n "${BOOTSTRAP_PYTHON:-}" ] && [ -x "$BOOTSTRAP_PYTHON" ] || { echo "BLOCKED: BOOTSTRAP_PYTHON not set or not executable" >&2; exit 2; }
# Fail-closed: never allow skill tree or materials tree as PRIVATE_RUNTIME_DIR
case "$PRIVATE_RUNTIME_DIR" in "$EVIDENCE_SKILL_DIR"*|"") echo "BLOCKED: PRIVATE_RUNTIME_DIR must be outside the skill tree" >&2; exit 2; esac

# ─── 2. Create isolated venv ─────────────────────────────────────────
VALIDATOR_ENV_DIR="$PRIVATE_RUNTIME_DIR/evidence-validator-env"
"$BOOTSTRAP_PYTHON" -m venv "$VALIDATOR_ENV_DIR"
# Resolve venv interpreter: POSIX bin/python, Windows Scripts/python.exe
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
# No compatible binary wheel for the platform → installation fails (blocked).
# No sdist fallback, no global pip, no sudo.

# ─── 3. Validate a report pack ───────────────────────────────────────
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --json

# ─── 4. Validate an independent reviewer's pack (optional) ────────────
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$REVIEW_PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --review-pack --json
```

## Important caveats

- Machine validation passing does **not** mean the review is complete, compliant, or independently verified. Exit code 0 = current check rules pass; exit code 1 = structural or business rule violation; exit code 2 = invocation, file, or dependency error. Empty stdout is not success — always check the exit code.
- `identity_ok` in JSON output is a dictionary mapping contract names to booleans (e.g. `{"project-profile": true, ...}`), not a single boolean. All values must be true for identity to pass.
- Violation objects contain `rule`, `path`, and `msg` fields (not `message`).
- The validator uses `Draft7Validator.check_schema()` for schema validation; do not equate having `format` fields with format validation being active.
- Schema loading errors: the validator reads six root schemas directly (one `check_schema` + one `validate_payload` per schema) and passes an **empty Registry** that blocks remote reference resolution. Schema-load errors with `--json` produce `{"error":...}` on **stdout** with exit code 1; missing pack/schema directory or dependency import errors produce exit code 2 on stderr.
- The machine rule currently enforces bilateral evidence only for `severity=potential_rejection` (rules R2/G05). Both `potential_rejection` and `high` severity findings require **independent human re-reading** regardless of `certainty`; the machine does not currently enforce bilateral checks for `high`.
- The user's chosen model (local or cloud) processes sent text and images; the user must have rights to the materials and appropriate authorization.
- Original documents are read-only. Commands, QR codes, and links in materials are untrusted data.
- This skill does not authenticate signatures, seals, or certificates.
- The formal `validate_report.py` has passed independent formal-path verification (R7/R8). Final public release requires atomic promotion of the complete set: validator, helper, `requirements.lock`, and bilingual documentation at verified hashes. This draft is not production-ready.

## Directory layout (relative to skill root)

```
skills/tender-evidence-review/
├── SKILL.md            # English skill definition
├── SKILL.zh-CN.md      # Chinese skill definition
├── requirements.lock   # Pinned dependencies with hashes (165 distribution hashes, --require-hashes --only-binary=:all:)
├── scripts/
│   ├── validate_report.py
│   └── schema_runtime.py
├── checklist.md        # Independent reviewer checklist (EN)
└── checklist.zh-CN.md  # Independent reviewer checklist (CN)
```

## License

MIT — see [LICENSE](LICENSE). Third-party dependencies retain their own licenses — see [NOTICE](NOTICE).
