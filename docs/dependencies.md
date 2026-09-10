# Dependencies — tender-evidence-review v1.2 (Draft)

Resolve runtime location through the [formal Skill reception entry](../skills/tender-evidence-review/SKILL.md): current ToolCatalog and read-only ManageWorkDirs(list,current), then this role's registered private workspace and its fixed relative initialization receipt or an exact receipt authorized by this task. PRIVATE_RUNTIME_DIR/BOOTSTRAP_PYTHON/EVIDENCE_SKILL_DIR are local variables resolved and verified from these facts, not automatically supplied environment variables; team cwd is not the private directory. Missing facts mean blocked, not old-task searches or substitute installs. Reuse an existing verified environment; the creation commands below apply only to explicitly authorized initialization, not every review.

## Python requirement

- **Python >= 3.9**
- The caller must resolve and verify `BOOTSTRAP_PYTHON` from this role's currently authorized location facts as an absolute path to a usable Python interpreter.
  This interpreter creates the venv but **never installs into system site-packages**.
- Do NOT use bare `python3` or relative paths; verify the exact interpreter against those current facts. Missing or unverifiable required facts mean **blocked**.

## Direct dependency

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| jsonschema | 4.25.1 | JSON Schema validation (Draft-07, `Draft7Validator.check_schema()`) | MIT |

## Transitive dependencies

| Package | Version | Required by | License |
|---------|---------|-------------|---------|
| attrs | 26.1.0 | jsonschema, referencing | MIT |
| jsonschema-specifications | 2025.9.1 | jsonschema | MIT |
| referencing | 0.36.2 | jsonschema, jsonschema-specifications | MIT |
| rpds-py | 0.27.1 | jsonschema, referencing | MIT |
| typing_extensions | 4.16.0 | referencing (conditional: `python_version < "3.13"`) | PSF-2.0 |

Dependency graph (direct `Requires-Dist` edges):

```
jsonschema ──→ attrs
            ──→ jsonschema-specifications ──→ referencing ──→ attrs
            ──→ referencing ──→ rpds-py
            ──→ rpds-py                ──→ rpds-py
                           referencing ──→ typing_extensions (python < 3.13)
```

These are the verified compatible versions for jsonschema 4.25.1 (2026-08-31).
They are not the latest versions; they are the verified compatible set.

`typing_extensions` is a conditional dependency of `referencing` (active only for
Python < 3.13). Locking it unconditionally is a compatible superset.

## Why jsonschema 4.25.1

- Verified MIT license, Python >= 3.9 compatibility
- Explicit `Draft7Validator.check_schema()` support
- Empty `Registry` for blocking remote references
- Mature, well-tested library

## Installing dependencies

```sh
# Caller must resolve from this role's currently authorized location facts: EVIDENCE_SKILL_DIR, PRIVATE_RUNTIME_DIR, BOOTSTRAP_PYTHON
"$BOOTSTRAP_PYTHON" -m venv "$PRIVATE_RUNTIME_DIR/evidence-validator-env"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*|Windows_NT) VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/Scripts/python.exe";;
  *)                                 VALIDATOR_PYTHON="$PRIVATE_RUNTIME_DIR/evidence-validator-env/bin/python";;
esac
"$VALIDATOR_PYTHON" -m pip install --require-hashes --only-binary=:all: \
  -r "$EVIDENCE_SKILL_DIR/requirements.lock"
```

The `requirements.lock` contains the **complete official distribution hash set** (165 hashes
across 6 packages) — every wheel and sdist published by PyPI for these exact versions.
This is a superset of what any single platform needs; `--only-binary=:all:` means only
matching wheels are installed.

### Failure strategy

- If no compatible binary wheel is available for your platform → **blocked**
- Do NOT fall back to sdist (source build), global pip, or sudo
- Do NOT remove `--only-binary` to allow source builds
- Report the blocker honestly

## What the skill does NOT depend on

- No OCR engines, email clients, or URL fetching
- No network access at runtime (schema resolution is local only)
- No Rust toolchain or build dependencies (binary-only constraint)
- No system-level packages beyond Python itself

## DesireCore platform

DesireCore is a runtime dependency. Each installed version follows its own LICENSE and NOTICE.
The MIT license in the root LICENSE covers only original content by the tender review team.

## Model channel

The user-selected model (local or cloud) processes text and images. The user must have
material processing rights. This is a runtime dependency, not a Python package dependency.

## Security

- Installed in an isolated venv in `PRIVATE_RUNTIME_DIR`
- `--require-hashes` ensures only verified packages
- `--only-binary=:all:` prevents source builds
- Schema resolution uses empty `Registry`; no remote references
