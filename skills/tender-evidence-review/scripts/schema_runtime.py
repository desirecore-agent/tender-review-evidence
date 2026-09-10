#!/usr/bin/env python3
"""schema_runtime.py — load/identity-check/validate Draft-07 JSON Schemas + payloads.

Requirements: jsonschema>=4.18, referencing. No HTTP access.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker
from referencing import Registry

# The six contract schema names (file basename without .schema.json)
CONTRACT_NAMES = [
    "project-profile",
    "file-manifest",
    "requirements",
    "coverage",
    "findings",
    "review-report",
]


def load_contracts(schema_dir: str) -> dict[str, dict]:
    """Load and Draft7-check-schema the six v1.2 contracts from *schema_dir*.

    Returns ``{name: schema_dict}``. Raises on missing file or invalid schema.
    """
    schemas: dict[str, dict] = {}
    base = Path(schema_dir)
    for name in CONTRACT_NAMES:
        path = base / f"{name}.schema.json"
        if not path.is_file():
            raise FileNotFoundError(f"Schema file not found: {path}")
        with open(path, encoding="utf-8") as fh:
            schema = json.load(fh)
        Draft7Validator.check_schema(schema)
        schemas[name] = schema
    return schemas


def check_contract_identity(schema_name: str, schema: dict) -> bool:
    """Return True iff schema is a dict with exact v1.2 identity.

    Checks (all exact-match, no substring/contains):
    - schema is a dict (rejects boolean/null)
    - ``$schema`` == ``http://json-schema.org/draft-07/schema#``
    - ``$id`` == ``tender-review/contracts/v1.2/schemas/{schema_name}.schema.json``
    - ``required`` includes "contract_version"
    - ``properties.contract_version.const`` == "v1.2"
    """
    if not isinstance(schema, dict):
        return False
    if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
        return False
    expected_id = f"tender-review/contracts/v1.2/schemas/{schema_name}.schema.json"
    if schema.get("$id") != expected_id:
        return False
    required = schema.get("required", [])
    if "contract_version" not in required:
        return False
    props = schema.get("properties", {})
    cv = props.get("contract_version", {})
    if not isinstance(cv, dict) or cv.get("const") != "v1.2":
        return False
    return True


def validate_payload(
    schema_name: str, schema: dict, payload: dict
) -> dict:
    """Validate *payload* against *schema* (Draft-07 + FormatChecker).

    Returns ``{"valid": bool, "errors": [str]}``.
    Uses an empty local Registry (no remote resolution).
    """
    registry = Registry()
    try:
        validator = Draft7Validator(
            schema,
            format_checker=FormatChecker(),
            registry=registry,
        )
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    except Exception as exc:
        return {"valid": False, "errors": [f"Schema setup error: {exc}"]}
    return {"valid": len(errors) == 0, "errors": [e.message for e in errors]}


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Load contract schemas, check identity, validate payloads."
    )
    parser.add_argument(
        "--schema-dir", required=True, help="Directory containing the six .schema.json files"
    )
    parser.add_argument(
        "--pack",
        required=True,
        help="Directory containing the six payload .json files to validate",
    )
    args = parser.parse_args()

    # 1. Load contracts
    try:
        contracts = load_contracts(args.schema_dir)
    except Exception as exc:
        print(json.dumps({"error": f"load_failed: {exc}"}), file=sys.stderr)
        return 2

    # 2. Check identity
    identity_ok: dict[str, bool] = {}
    for name, schema in contracts.items():
        try:
            identity_ok[name] = check_contract_identity(name, schema)
        except Exception as exc:
            identity_ok[name] = False
            print(json.dumps({"error": f"identity_check_failed/{name}: {exc}"}), file=sys.stderr)
            return 2

    if not all(identity_ok.values()):
        print(json.dumps({"error": "identity_failed", "identity_ok": identity_ok}), file=sys.stderr)
        return 2

    # 3. Validate payloads
    pack_dir = Path(args.pack)
    if not pack_dir.is_dir():
        print(json.dumps({"error": f"pack_dir_not_found: {pack_dir}"}), file=sys.stderr)
        return 2

    validation: dict[str, dict] = {}
    for name in CONTRACT_NAMES:
        payload_path = pack_dir / f"{name}.json"
        if not payload_path.is_file():
            validation[name] = {"valid": False, "errors": [f"payload file not found: {payload_path}"]}
            continue
        with open(payload_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        validation[name] = validate_payload(name, contracts[name], payload)

    # 4. Decide exit code
    all_valid = all(v["valid"] for v in validation.values())
    exit_code = 0 if all_valid else 1

    # 5. Output
    output = {
        "contracts_loaded": len(contracts),
        "identity_ok": identity_ok,
        "validation": validation,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(_cli())
