# Optional structured-export dependencies

Substantive evidence review does not require a Python environment. These dependencies apply only when the user explicitly requests validation of the retained v1.2 six-product JSON export.

Use Python 3.9+ and the bundled `skills/tender-evidence-review/requirements.lock` (jsonschema 4.25.1 and pinned transitive packages; licenses in NOTICE). Resolve a permitted interpreter, the installed skill directory, team schema directory and a writable isolated environment from the current workspace. Reuse a suitable environment. If initialization is needed, create a venv in an authorized workspace and install with `pip install --require-hashes --only-binary=:all: -r <lock-path>`. Do not install globally or modify source materials. No compatible wheel means export validation is unavailable; narrative review can continue.

Run:

```sh
"$VALIDATOR_PYTHON" "$EVIDENCE_SKILL_DIR/scripts/validate_report.py" \
  --pack "$PACK_DIR" --schemas "$TEAM_ROOT/shared/contracts/schemas" --json
```

Variables denote actual authorized paths, not automatically supplied environment variables. The script checks local JSON and internal consistency; it does not independently read business source documents or establish their truth. Record actual failures and correct affected exports without inventing facts. See [recovery](recovery.md).

The selected model channel processes supplied text/images according to its deployment. Additional OCR or external services are not implied by installing this skill.
