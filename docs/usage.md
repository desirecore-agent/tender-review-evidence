# Usage Guide — tender-evidence-review v1.2 (Draft)

Resolve runtime location through the [formal Skill reception entry](../skills/tender-evidence-review/SKILL.md): current ToolCatalog and read-only ManageWorkDirs(list,current), then this role's registered private workspace and its fixed relative initialization receipt or an exact receipt authorized by this task. PRIVATE_RUNTIME_DIR/BOOTSTRAP_PYTHON/EVIDENCE_SKILL_DIR are local variables resolved and verified from these facts, not automatically supplied environment variables; team cwd is not the private directory. Missing facts mean blocked, not old-task searches or substitute installs. Reuse an existing verified environment; the creation commands below apply only to explicitly authorized initialization, not every review.

## Prerequisites

- Python >= 3.9
- jsonschema 4.25.1 and all transitive dependencies (see `requirements.lock`)
- Team shared contracts v1.2 schemas at `<TEAM_ROOT>/shared/contracts/schemas/`
- Caller-resolved and verified absolute paths (not automatically injected platform variables): `EVIDENCE_SKILL_DIR`, `PRIVATE_RUNTIME_DIR`, `BOOTSTRAP_PYTHON`

## Setting up the validator environment

```sh
# ─── 0. Caller resolves and verifies these absolute paths from current authorized facts ────────────────────
# EVIDENCE_SKILL_DIR : absolute path to this skill root (not in materials/pack tree)
# PRIVATE_RUNTIME_DIR : per-user per-agent private directory (absolute, writable, outside skill tree)
# BOOTSTRAP_PYTHON : absolute path to Python >=3.9 (used only for venv creation)

# ─── 1. Guard required variables ──────────────────────────────────────
[ -n "${EVIDENCE_SKILL_DIR:-}" ] && [ -d "$EVIDENCE_SKILL_DIR" ] || { echo "BLOCKED: EVIDENCE_SKILL_DIR not set or not a directory" >&2; exit 2; }
[ -n "${PRIVATE_RUNTIME_DIR:-}" ] && [ -d "$PRIVATE_RUNTIME_DIR" ] || { echo "BLOCKED: PRIVATE_RUNTIME_DIR not set or not a directory" >&2; exit 2; }
[ -n "${BOOTSTRAP_PYTHON:-}" ] && [ -x "$BOOTSTRAP_PYTHON" ] || { echo "BLOCKED: BOOTSTRAP_PYTHON not set or not executable" >&2; exit 2; }
case "$PRIVATE_RUNTIME_DIR" in "$EVIDENCE_SKILL_DIR"*|"") echo "BLOCKED: PRIVATE_RUNTIME_DIR must be outside the skill tree" >&2; exit 2; esac

# ─── 2. Create isolated venv ─────────────────────────────────────────
VALIDATOR_ENV_DIR="$PRIVATE_RUNTIME_DIR/evidence-validator-env"
"$BOOTSTRAP_PYTHON" -m venv "$VALIDATOR_ENV_DIR"
# Resolve venv interpreter per OS
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$VALIDATOR_ENV_DIR/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
# If no compatible binary wheel → installation fails (blocked). No sdist fallback.
```

If the caller cannot resolve and verify the required variables from this role's currently authorized location facts, **stop**. Do not guess `cwd`, bare `python3`, or relative paths.

## Validating a report pack

### Basic validation (six-file gate)

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --json
```

The pack directory must contain all six JSON files:
`project-profile.json`, `file-manifest.json`, `requirements.json`,
`coverage.json`, `findings.json`, `review-report.json`.

### Validating an independent reviewer's pack

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$REVIEW_PACK_DIR" \
  --schemas "$TEAM_ROOT/shared/contracts/schemas" \
  --review-pack --json
```

`--review-pack` is a format gate allowing `review_status` values of `reviewed_confirmed`, `reviewed_downgraded`, and `reviewed_withdrawn` (author packs must not contain these). Actual independent execution is evidenced by run records and product receipts, not by the flag alone.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All current check rules passed |
| 1 | Structural violation or business rule failure; **also** Schema-load errors with `--json` (error written to stdout) |
| 2 | Invocation, file, or dependency import error (error on stderr) |

Schema loading errors with `--json` produce `{"error":...}` on **stdout** with exit code 1. Missing pack/schema directory or dependency import errors produce exit code 2 on stderr. Do not assume all errors go to stderr.

### JSON output

- `result`: "pass" or "fail"
- `violation_count`: number of violations
- `violations`: `{rule, path, msg}` objects (not `message`)
- `identity_ok`: contract-name→boolean dictionary (not a single boolean); all must be true
- `artifact_states`: per-product state (`object`, `null`, `parse_error`, `absent`)
- `artifacts_present`, `artifacts_missing`, `artifacts_invalid`

**Do not treat empty stdout as success.** Always check exit code and parse output.

## What the validator checks

### Schema validation (jsonschema Draft-07)

- `Draft7Validator.check_schema()` explicitly verifies each schema before instance validation
- A local **empty `Registry`** blocks remote reference resolution; the `--schemas` directory is NOT pre-registered as a cross-resource Registry
- Having `format` fields in schemas does not mean format validation is active

### Business rules

Machine currently enforces R2/G05 bilateral evidence **only** for `severity=potential_rejection`. Both `potential_rejection` and `high` severity findings require **independent human re-reading** regardless of `certainty`, but the machine does not enforce bilateral checks for `high`.

Other machine checks: R1, R3, R4, R5, R6, G02–G08 (see SKILL.md for full table).

## Workflow example

```
1. Lead completes initial review → produces author pack
2. Independent reviewer runs validator on author pack
   → any violations recorded before human re-reading
3. Independent reviewer performs human re-reading:
   - Re-read bilateral evidence for ALL potential_rejection AND high severity findings
   - Search negative examples
   - Re-compute calculations
   - Validate image observation records (any manifest source, not just image files)
   - Re-count coverage closure (checked/failed/unchecked end-states)
4. Reviewer produces review pack with review_status updates
5. Reviewer runs validator on review pack (with --review-pack)
6. Reviewer records confirmation/downgrade/withdrawal with complete issue_id and reasons
7. Final pack delivered to team lead for merge
```

## Important caveats

- **Machine pass ≠ review complete**: Independent human re-reading is a separate, mandatory step.
- **Templates are not evidence**: A correctly structured template with placeholder values is not an executed review.
- **Partial delivery is honest**: `conclusion=partial_only` with honest coverage is valid and passes structure checks.
- **Model channel processing**: Text and images sent to the model are processed by the model provider. The user must have material processing rights.
- **This is a draft package**: The formal validator has passed R7/R8, but final release requires atomic promotion of the complete verified set. This documentation is a publication draft, not production-ready.
