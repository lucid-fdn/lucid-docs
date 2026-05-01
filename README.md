# Lucid Docs

Public Mintlify documentation for Lucid.

## Local Preview

Install the Mintlify CLI, then run the docs site from this repository root:

```bash
npm i -g mint
mint dev
```

## SDK Documentation Sync

SDK pages are generated from the current Speakeasy TypeScript SDK docs in
[`lucid-fdn/lucid-ai-sdk`](https://github.com/lucid-fdn/lucid-ai-sdk).

Regenerate locally:

```bash
python scripts/rebuild-sdk-docs.py
python scripts/validate-docs.py
```

The GitHub Actions workflow `.github/workflows/sync-sdk-docs.yml` runs the same
sync every 6 hours, can be triggered manually, and also accepts
`repository_dispatch` events from the SDK repo.

## API Reference

Mintlify generates the endpoint reference from:

```text
https://raw.githubusercontent.com/lucid-fdn/lucid-ai-sdk/main/openapi-with-code-samples.yaml
```
