#!/usr/bin/env python3
"""Rebuild Mintlify SDK docs from the current generated TypeScript SDK docs.

The source of truth is the Speakeasy-generated SDK repository:
https://github.com/lucid-fdn/lucid-ai-sdk

This script intentionally has no third-party dependencies so it can run in
GitHub Actions on a clean Python install.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
import urllib.error
import urllib.request
import posixpath
from pathlib import Path
from typing import Any


DOCS_ROOT = Path(os.environ.get("DOCS_ROOT", Path(__file__).resolve().parents[1]))
SDK_OWNER_REPO = os.environ.get("SDK_OWNER_REPO", "lucid-fdn/lucid-ai-sdk")
SDK_BRANCH = os.environ.get("SDK_BRANCH", "main")
RAW_BASE = f"https://raw.githubusercontent.com/{SDK_OWNER_REPO}/{SDK_BRANCH}"
API_BASE = f"https://api.github.com/repos/{SDK_OWNER_REPO}/contents"
HEADERS = {"User-Agent": "lucid-docs-sdk-sync"}

CORE_NAMESPACES = [
    "passports",
    "match",
    "run",
    "receipts",
    "epochs",
    "payouts",
    "compute",
    "health",
    "agents",
    "deploy",
    "memory",
    "payments",
    "webhooks",
]

NAMESPACE_DESCRIPTIONS = {
    "a2a": "Agent-to-agent messaging and coordination.",
    "agents": "AI agent orchestration, planning, and execution.",
    "agentscrosschain": "Cross-chain agent operations.",
    "anchoring": "Receipt and epoch anchoring operations.",
    "chains": "Supported chain and network metadata.",
    "compute": "Compute node registration, health, and routing.",
    "crosschain": "Cross-chain coordination helpers.",
    "deploy": "Agent deployment workflows.",
    "disputes": "Dispute lifecycle operations.",
    "epochs": "Epoch lifecycle, anchoring, and verification.",
    "escrow": "Escrow and settlement operations.",
    "health": "System and dependency health checks.",
    "identity": "Identity and account primitives.",
    "launch": "Agent launch flows.",
    "match": "Model and resource matching.",
    "memory": "Agent memory operations.",
    "mirror": "Mirroring and projection operations.",
    "modules": "Runtime module metadata.",
    "passports": "Identity passports for models, compute, tools, datasets, and agents.",
    "paymaster": "Gas and paymaster operations.",
    "payments": "Payment and billing primitives.",
    "payouts": "Payout calculations and settlement records.",
    "payoutscrosschain": "Cross-chain payout operations.",
    "receipts": "Cryptographic receipts and verification.",
    "reputation": "Reputation records and scoring.",
    "reputationcrosschain": "Cross-chain reputation operations.",
    "revenue": "Revenue and share accounting.",
    "run": "Inference and runtime execution.",
    "shares": "Revenue share and ownership operations.",
    "tba": "Token-bound account operations.",
    "wallet": "Wallet and account helpers.",
    "webhooks": "Webhook subscriptions and delivery.",
    "zkml": "ZKML verification operations.",
}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc


def fetch_json(url: str) -> Any:
    return json.loads(fetch_text(url))


def write_file(relative_path: str, content: str) -> None:
    path = DOCS_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"updated {relative_path}")


def slug_title(slug: str) -> str:
    known = {
        "a2a": "A2A",
        "zkml": "ZKML",
        "tba": "TBA",
    }
    if slug in known:
        return known[slug]
    return re.sub(r"(?<!^)([A-Z])", r" \1", slug).replace("-", " ").replace("_", " ").title()


def strip_generated_comments(markdown: str) -> str:
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL).strip()


def normalize_markdown(markdown: str) -> str:
    markdown = strip_generated_comments(markdown)
    markdown = markdown.replace("https://github.com/raijinlabs/lucid-ai-sdk", "https://github.com/lucid-fdn/lucid-ai-sdk")
    markdown = markdown.replace("[!NOTE]", "info")
    markdown = markdown.replace("[!WARNING]", "warning")
    return markdown.strip()


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def demote_headings(markdown: str, levels: int = 1) -> str:
    def replace(match: re.Match[str]) -> str:
        hashes = match.group(1)
        title = match.group(2)
        return f"{'#' * min(6, len(hashes) + levels)} {title}"

    return re.sub(r"^(#{1,6})\s+(.+)$", replace, markdown, flags=re.MULTILINE)


def rewrite_relative_links(markdown: str, source_dir: str) -> str:
    def replace(match: re.Match[str]) -> str:
        href = match.group(1)
        if href.startswith(("#", "http://", "https://", "mailto:")):
            return match.group(0)
        if not href.endswith(".md") and ".md#" not in href:
            return match.group(0)

        normalized = posixpath.normpath(posixpath.join(source_dir, href))
        return f"](https://github.com/lucid-fdn/lucid-ai-sdk/blob/main/{normalized})"

    return re.sub(r"\]\(([^)]+)\)", replace, markdown)


def extract_code_blocks(markdown: str, language: str = "typescript", limit: int = 3) -> list[str]:
    pattern = re.compile(rf"```(?:{language}|ts)\n(.*?)```", re.DOTALL)
    return [match.group(1).strip() for match in pattern.finditer(markdown)][:limit]


def extract_summary(markdown: str) -> str:
    match = re.search(r"## Summary[ \t]*\n+(.*?)(?:\n## |\Z)", markdown, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def discover_namespaces() -> list[str]:
    items = fetch_json(f"{API_BASE}/typescript/docs/sdks?ref={SDK_BRANCH}")
    namespaces = sorted(item["name"] for item in items if item.get("type") == "dir")
    if not namespaces:
        raise RuntimeError("No SDK namespaces found in generated SDK docs.")
    return namespaces


def fetch_namespace_readme(namespace: str) -> str:
    return fetch_text(f"{RAW_BASE}/typescript/docs/sdks/{namespace}/README.md")


def extract_operations(namespace_readme: str) -> list[tuple[str, str]]:
    operations: list[tuple[str, str]] = []
    for line in namespace_readme.splitlines():
        match = re.match(r"\*\s+\[([^\]]+)\]\([^)]+\)\s+-\s+(.+)", line.strip())
        if match:
            operations.append((match.group(1).strip(), match.group(2).strip()))
    return operations


def extract_overview(namespace_readme: str) -> str:
    match = re.search(r"## Overview[ \t]*\n+(.*?)(?:\n### Available Operations|\n## |\Z)", namespace_readme, re.DOTALL)
    if not match:
        return ""
    overview = " ".join(match.group(1).strip().split())
    if not overview or overview.startswith("###"):
        return ""
    return overview


def namespace_description(namespace: str, readme: str) -> str:
    overview = extract_overview(readme)
    return overview or NAMESPACE_DESCRIPTIONS.get(namespace, f"{slug_title(namespace)} SDK operations.")


def render_method_table(operations: list[tuple[str, str]]) -> str:
    if not operations:
        return "No generated operations were found for this namespace."
    rows = ["| Method | Description |", "| --- | --- |"]
    for method, description in operations:
        rows.append(f"| `{method}` | {escape_table_cell(description)} |")
    return "\n".join(rows)


def render_namespace_page(namespace: str, readme: str) -> str:
    title = f"{slug_title(namespace)} SDK"
    description = namespace_description(namespace, readme)
    operations = extract_operations(readme)
    body = rewrite_relative_links(normalize_markdown(readme), f"typescript/docs/sdks/{namespace}")
    body = re.sub(r"^# .+?\n+", "", body, count=1)
    body = demote_headings(body, 1)
    return f"""---
title: {yaml_string(title)}
description: {yaml_string(description)}
---

# {title}

{description}

## Operations

{render_method_table(operations)}

## Generated Reference

{body}
"""


def render_typescript_page(readme: str, runtimes: str, namespaces: list[str], namespace_docs: dict[str, str]) -> str:
    summary = extract_summary(readme) or "Type-safe TypeScript SDK for the LucidLayer API."
    examples = extract_code_blocks(readme, limit=2)
    quick_start = examples[0] if examples else (
        'import { RaijinLabsLucidAi } from "raijin-labs-lucid-ai";\n\n'
        'const sdk = new RaijinLabsLucidAi({ serverURL: "https://api.lucid.foundation" });\n'
        'const health = await sdk.health.checkSystemHealth();'
    )
    rows = ["| Namespace | Description | Operations |", "| --- | --- | ---: |"]
    for namespace in namespaces:
        readme_for_ns = namespace_docs[namespace]
        rows.append(
            f"| [`sdk.{namespace}`](/sdks/namespaces/{namespace}) | "
            f"{escape_table_cell(namespace_description(namespace, readme_for_ns))} | "
            f"{len(extract_operations(readme_for_ns))} |"
        )
    runtime_excerpt = normalize_markdown(runtimes)
    runtime_excerpt = re.sub(r"^# .+?\n+", "", runtime_excerpt, count=1)
    return f"""---
title: "TypeScript SDK"
description: "Install and use the generated TypeScript SDK for the LucidLayer API."
---

# TypeScript SDK

{summary}

## Installation

```bash
npm install raijin-labs-lucid-ai
```

## Quick Start

```typescript
{quick_start}
```

## Authentication

```typescript
import {{ RaijinLabsLucidAi }} from "raijin-labs-lucid-ai";

const sdk = new RaijinLabsLucidAi({{
  serverURL: "https://api.lucid.foundation",
  // Add API key auth when the endpoint requires it.
  // security: {{ bearerAuth: process.env.LUCID_API_KEY }},
}});
```

## Namespaces

{os.linesep.join(rows)}

## Supported Runtimes

{runtime_excerpt}

## Source

- [SDK repository](https://github.com/lucid-fdn/lucid-ai-sdk/tree/main/typescript)
- [npm package](https://www.npmjs.com/package/raijin-labs-lucid-ai)
- [OpenAPI with code samples](https://raw.githubusercontent.com/lucid-fdn/lucid-ai-sdk/main/openapi-with-code-samples.yaml)
"""


def render_examples_page(usage: str, functions: str) -> str:
    usage_examples = extract_code_blocks(usage, limit=4)
    function_examples = extract_code_blocks(functions, limit=2)
    first_usage = usage_examples[0] if usage_examples else ""
    first_function = function_examples[0] if function_examples else ""
    return f"""---
title: "SDK Examples"
description: "Generated examples for common Lucid SDK usage."
---

# SDK Examples

These examples are rebuilt from the current generated TypeScript SDK docs.

## Inference Example

```typescript
{first_usage}
```

## Standalone Function Example

Standalone functions are useful for browser, edge, and serverless bundles where tree-shaking matters.

```typescript
{first_function}
```

## More Examples

- [Full TypeScript SDK overview](/sdks/typescript)
- [Namespace reference](/sdks/reference)
- [Generated SDK source](https://github.com/lucid-fdn/lucid-ai-sdk/tree/main/typescript)
"""


def render_reference_page(namespaces: list[str], namespace_docs: dict[str, str]) -> str:
    rows = ["| Namespace | Description | Operations |", "| --- | --- | ---: |"]
    total_operations = 0
    for namespace in namespaces:
        readme = namespace_docs[namespace]
        operations = extract_operations(readme)
        total_operations += len(operations)
        rows.append(
            f"| [`sdk.{namespace}`](/sdks/namespaces/{namespace}) | "
            f"{escape_table_cell(namespace_description(namespace, readme))} | {len(operations)} |"
        )

    core_links = [
        f"- [`sdk.{namespace}`](/sdks/namespaces/{namespace})"
        for namespace in CORE_NAMESPACES
        if namespace in namespace_docs
    ]

    return f"""---
title: "SDK Reference"
description: "Generated namespace index for the Lucid TypeScript SDK."
---

# SDK Reference

This page is generated from the current Speakeasy SDK docs in `lucid-fdn/lucid-ai-sdk`.

## Summary

- Namespaces: `{len(namespaces)}`
- Operations: `{total_operations}`
- Package: `raijin-labs-lucid-ai`
- API base URL: `https://api.lucid.foundation`

## Common Namespaces

{os.linesep.join(core_links)}

## All Namespaces

{os.linesep.join(rows)}
"""


def update_docs_json(namespaces: list[str]) -> None:
    path = DOCS_ROOT / "docs.json"
    docs_json = json.loads(path.read_text(encoding="utf-8"))
    namespace_pages = [f"sdks/namespaces/{namespace}" for namespace in namespaces]

    for tab in docs_json.get("navigation", {}).get("tabs", []):
        if tab.get("tab") != "API & SDK":
            continue
        for group in tab.get("groups", []):
            if group.get("group") == "API Endpoints":
                group["openapi"] = "/openapi-spec.yaml"
            if group.get("group") == "SDKs":
                group["pages"] = ["sdks/typescript", "sdks/examples", "sdks/reference"]

        groups = tab.setdefault("groups", [])
        namespace_group = next((group for group in groups if group.get("group") == "SDK Namespaces"), None)
        if namespace_group is None:
            groups.append({"group": "SDK Namespaces", "pages": namespace_pages})
        else:
            namespace_group["pages"] = namespace_pages

    path.write_text(json.dumps(docs_json, indent=2) + "\n", encoding="utf-8")
    print("updated docs.json")


def main() -> None:
    print(f"docs root: {DOCS_ROOT}")
    print(f"sdk source: {SDK_OWNER_REPO}@{SDK_BRANCH}")

    readme = fetch_text(f"{RAW_BASE}/typescript/README.md")
    usage = fetch_text(f"{RAW_BASE}/typescript/USAGE.md")
    functions = fetch_text(f"{RAW_BASE}/typescript/FUNCTIONS.md")
    runtimes = fetch_text(f"{RAW_BASE}/typescript/RUNTIMES.md")
    openapi = fetch_text(f"{RAW_BASE}/openapi-with-code-samples.yaml")
    namespaces = discover_namespaces()
    namespace_docs = {namespace: fetch_namespace_readme(namespace) for namespace in namespaces}

    write_file("openapi-spec.yaml", openapi)
    write_file("sdks/typescript.mdx", render_typescript_page(readme, runtimes, namespaces, namespace_docs))
    write_file("sdks/examples.mdx", render_examples_page(usage, functions))
    write_file("sdks/reference.mdx", render_reference_page(namespaces, namespace_docs))

    for namespace in namespaces:
        write_file(f"sdks/namespaces/{namespace}.mdx", render_namespace_page(namespace, namespace_docs[namespace]))

    update_docs_json(namespaces)
    print(f"generated {len(namespaces)} namespace pages")


if __name__ == "__main__":
    main()
