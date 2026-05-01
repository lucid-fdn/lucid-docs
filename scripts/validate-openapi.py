#!/usr/bin/env python3
"""Validate the local OpenAPI artifact consumed by Mintlify."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate


ROOT = Path(__file__).resolve().parents[1]
DOCS_JSON = ROOT / "docs.json"


def iter_local_openapi_refs(node: Any):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "openapi" and isinstance(value, str) and not value.startswith(("http://", "https://")):
                yield value
            else:
                yield from iter_local_openapi_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_local_openapi_refs(item)


def main() -> int:
    filenames = sys.argv[1:]
    if not filenames:
        docs_json = json.loads(DOCS_JSON.read_text(encoding="utf-8"))
        filenames = sorted(set(iter_local_openapi_refs(docs_json)))
        if not filenames:
            print("No local OpenAPI references found in docs.json.", file=sys.stderr)
            return 1

    for filename in filenames:
        path = Path(filename)
        if filename.startswith("/") and not path.exists():
            path = ROOT / filename.lstrip("/")
        elif not path.is_absolute():
            path = ROOT / path
        with path.open(encoding="utf-8") as handle:
            spec = yaml.safe_load(handle)
        validate(spec)
        try:
            display_path = path.relative_to(ROOT)
        except ValueError:
            display_path = path
        print(f"OpenAPI validation passed: {display_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
