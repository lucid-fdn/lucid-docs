# Lucid Documentation

## What This Is
Public developer documentation for Lucid — the coordination and settlement layer for autonomous agents. Built with Mintlify, auto-deployed on push to `main`.

## Quick Start
```bash
npm i -g mintlify
mintlify dev          # Local preview at localhost:3000
```

## Structure (8 tabs, ~65 pages)
```
Get Started:      index, quickstart, install-agent, architecture
Build & Deploy:   deploy/{from-telegram, from-cli, from-source, from-image, from-catalog,
                         setup-wizard, secrets, channels, runtime-config,
                         hosted-models, bring-your-model, model-routing,
                         compute-selection, depin, gpu-routing}
How Lucid Works:  how/{execution-*, coordination-*, settlement-*}
Core Concepts:    concepts/{passports, memory, compute-models, agent-deployment,
                           agent-orchestration, payments, receipts, anchoring, reputation}
Gateway:          gateway/{trustgate, mcpgate, control-plane, channels}
API & SDK:        api-reference/{introduction, errors, rate-limits} + OpenAPI auto-render + sdks/
On-Chain:         on-chain/{solana-overview, thought-epoch, lucid-passports, ...}
More:             advanced/{self-hosting, configuration, custom-agents, extending-runtime, contributing}
```

## How Pages Are Produced

### Three production methods

| Method | Pages | Source | Updates |
|--------|-------|--------|---------|
| Hand-written | 7 | Human-authored (Get Started + API intro) | Manual |
| AI Pipeline | ~48 | Auto-generated from source code | On push to Lucid-L2 or platform-core |
| Mintlify OpenAPI | ~175 endpoints | openapi.yaml | Auto on deploy |

### AI Generation Pipeline

The pipeline lives in `Lucid-L2/tools/docs/` and generates pages from multiple source types:

```
Source Adapters
├── TypeScriptAdapter   — ts-morph extracts barrel exports from engine/src/
│                         Covers: Core Concepts, On-Chain programs/contracts
│
├── ClaudeMdAdapter     — parses CLAUDE.md sections by heading
│                         Covers: Build & Deploy, How Lucid Works, Gateway, Advanced
│                         Sources: Lucid-L2/CLAUDE.md + lucid-plateform-core/CLAUDE.md
│
├── ReadmeAdapter       — parses README.md files
│                         Covers: Runtime, Self-Hosting, Contributing, Payments
│
└── EnvAdapter          — parses .env.example into config tables
                          Covers: Configuration page

All adapters → PageSource → AI Enrichment (TrustGate) → Mintlify .mdx
```

### How to regenerate pages

```bash
# From Lucid-L2/tools/docs/:

# Generate all pages (adapters + reference + mintlify sync)
TRUSTGATE_API_KEY=... TRUSTGATE_URL=... npx tsx src/generate.ts --artifact pages --output /path/to/lucid-docs

# Generate from a specific adapter only
npx tsx src/generate.ts --artifact pages --adapter claude-md

# Generate reference docs only (deterministic, no AI)
npx tsx src/generate.ts --artifact reference

# Generate everything (all artifacts)
npx tsx src/generate.ts
```

### AI enrichment flow

1. Adapter extracts raw markdown from source file (CLAUDE.md section, README, .env)
2. If `needsEnrichment: true`, sends to TrustGate (OpenAI-compatible) with prompt:
   - "Rewrite for a developer who has never seen Lucid"
   - "Remove internal file paths, keep code examples and tables"
   - "Output MDX body only, no frontmatter"
3. Page renderer wraps with Mintlify frontmatter (title, description)
4. Writes .mdx to output directory

### Cache

Generated pages are cached by source file hash. If the source hasn't changed, the page is skipped. Cache is gitignored — CI always regenerates fresh.

### CI auto-sync (planned)

GitHub Action on `Lucid-L2` triggers on push to master when source files change. Runs the pipeline, pushes generated .mdx files to this repo. Mintlify auto-deploys on push.

## Which pages are hand-written?

Only these 7 pages are manually maintained:

1. `index.mdx` — "What is Lucid" positioning narrative
2. `quickstart.mdx` — 2-min Telegram-first agent launch
3. `install-agent.mdx` — detailed Telegram walkthrough
4. `architecture.mdx` — 3-layer model + 4-layer infra
5. `api-reference/introduction.mdx` — API overview
6. `api-reference/errors.mdx` — error codes
7. `api-reference/rate-limits.mdx` — rate limiting

Everything else is generated. If you edit a generated page directly, it will be overwritten on next pipeline run.

## Config
- `docs.json` — Mintlify v2 config (Aspen theme, Montserrat font)
- OpenAPI source: `github.com/lucid-fdn/Lucid-L2/master/openapi.yaml`
- Primary color: `#6366F1` (indigo)

## Branding
- Docs: `docs.lucid.foundation`
- Dashboard: `app.lucid.foundation`
- API: `api.lucid.foundation`
- Telegram Bot: `@mylclaw_bot`

## Remote
`github.com/lucid-fdn/lucid-docs` — branch: `main`, auto-deploy via Mintlify GitHub App
