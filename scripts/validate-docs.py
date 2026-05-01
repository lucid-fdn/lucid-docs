#!/usr/bin/env python3
"""Lightweight docs validation for the Mintlify repo."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS_JSON = ROOT / "docs.json"


def iter_pages(node: Any):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pages" and isinstance(value, list):
                for page in value:
                    if isinstance(page, str) and not page.startswith(("GET ", "POST ", "PATCH ", "PUT ", "DELETE ")):
                        yield page
            else:
                yield from iter_pages(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_pages(item)


def validate_page_exists(page: str) -> str | None:
    path = ROOT / f"{page}.mdx"
    if not path.exists():
        return f"Missing docs.json page target: {page}.mdx"
    if not path.read_text(encoding="utf-8").strip():
        return f"Empty docs page: {page}.mdx"
    return None


def validate_openapi_urls(node: Any) -> list[str]:
    errors: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "openapi" and isinstance(value, str) and value.startswith("https://"):
                try:
                    with urllib.request.urlopen(
                        urllib.request.Request(value, headers={"User-Agent": "lucid-docs-validate"}),
                        timeout=20,
                    ) as response:
                        if response.status >= 400:
                            errors.append(f"OpenAPI URL returned HTTP {response.status}: {value}")
                except Exception as exc:
                    errors.append(f"OpenAPI URL is not reachable: {value} ({exc})")
            else:
                errors.extend(validate_openapi_urls(value))
    elif isinstance(node, list):
        for item in node:
            errors.extend(validate_openapi_urls(item))
    return errors


def main() -> int:
    docs = json.loads(DOCS_JSON.read_text(encoding="utf-8"))
    errors = []
    for page in sorted(set(iter_pages(docs))):
        error = validate_page_exists(page)
        if error:
            errors.append(error)
    errors.extend(validate_openapi_urls(docs))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Docs validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
