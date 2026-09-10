# Recovery Guide — tender-evidence-review v1.2 (Draft)

All recovery preserves auditability: no silent fixes, no overwriting original documents.

## Failure: Missing dependency (jsonschema not installed)

**Symptom**: Exit code 2; stderr: `{"error": "Cannot import schema_runtime: No module named 'jsonschema'"}`

**Recovery**:
```sh
# Ensure EVIDENCE_SKILL_DIR, PRIVATE_RUNTIME_DIR, BOOTSTRAP_PYTHON are set and guarded.
"$BOOTSTRAP_PYTHON" -m venv "$PRIVATE_RUNTIME_DIR/evidence-validator-env"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
```

No compatible binary wheel → **blocked**. No sdist fallback, no global pip, no sudo.

## Failure: Missing or corrupt schema

**Symptom**: Exit code 1 (with `--json`: `{"error":...}` on **stdout**); or exit code 2 (missing directory / import error on stderr).

**Recovery**:
1. Verify `--schemas` path points to `<TEAM_ROOT>/shared/contracts/schemas/`
2. Confirm all six `.schema.json` files exist and parse
3. Corrupt schema → **fail closed** (do not skip)

## Failure: Pack missing products

**Symptom**: Exit code 1; `artifact_states` shows `absent`.

**Recovery**: Six-file gate requires all six products. Record missing items; do not pass.

## Failure: `manifest_id` mismatch (G06)

**Symptom**: Exit code 1.

**Recovery**: Binding is `file-manifest.manifest_id` = `requirements.manifest_id` = `coverage.manifest_id` = `findings.manifest_id` = `review-report.inputs_version.manifest_id`; `project-profile` has no `manifest_id`. Do not edit to match — re-generate the stale product.

## Failure: Coverage closure mismatch (R3/G02)

**Symptom**: Exit code 1.

**Recovery**: Re-count from `items[]` using `checked`/`failed`/`unchecked` end-states (not "completed"). Verify `coverage_file_ids` covers full manifest minus explicitly excluded files.

## Key principles

1. **Fail closed**: When in doubt, reject.
2. **No silent fixes**: Every correction traceable.
3. **Originals read-only**: Recovery never modifies source documents or author packs.
4. **Honest partial**: `partial_only` is valid; it does not mean "pass."
5. **Binary-only**: No sdist, no global pip, no sudo.
6. **Platform-provided paths**: If `EVIDENCE_SKILL_DIR`, `PRIVATE_RUNTIME_DIR`, or `BOOTSTRAP_PYTHON` are not available → blocked.
