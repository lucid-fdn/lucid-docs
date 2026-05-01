# Public Docs Automation

Public docs are generated from `docs-automation.json` plus the SDK/OpenAPI
sync scripts. The goal is to make docs follow source changes without relying on
someone to remember which public page needs an update.

## Sources

`docs-automation.json` is the source registry. Each source declares:

- `repo`: owner/repo used for provenance.
- `rootEnv`: optional checkout path override used by CI.
- `localPath`: local fallback for development.
- `adapter`: how the source is read.
- `publicSafe`: whether the source can be published without per-file markers.
- `outputPrefix`: where generated pages are written.
- `navigationTab`: which Mintlify tab receives the generated pages.

Private repositories are deny-by-default. A private source is only published
when `publicSafe` is true in the registry or a document has `public: true` in
frontmatter / `<!-- lucid-public: true -->`.

## Generated Artifacts

Running `python scripts/rebuild-public-sources.py` writes:

- generated MDX pages from registered source repos
- `public-docs-manifest.json`
- `public-docs-inventory.json`
- `llms.txt`
- `llms-full.txt`
- copied GitBook image assets under `images/wiki/`

Running `python scripts/rebuild-sdk-docs.py` writes:

- `sdks/typescript.mdx`
- `sdks/examples.mdx`
- `sdks/reference.mdx`
- `sdks/namespaces/*.mdx`
- the API & SDK navigation in `docs.json`

## Validation

`python scripts/validate-docs.py` checks:

- every `docs.json` page target exists and is non-empty
- OpenAPI URLs are reachable
- every generated manifest target exists
- generated pages include provenance headers
- local links and local image paths resolve

## CI

`.github/workflows/sync-sdk-docs.yml` runs the public-source generator, SDK
generator, and validator before committing generated changes.

For private source repos, set `DOCS_SOURCE_TOKEN` with read access to:

- `lucid-fdn/lucid-wiki`
- `lucid-fdn/lucid-cloud`

Without that secret, public sources still update, but private-source generated
pages cannot refresh inside GitHub Actions.
