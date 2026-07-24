# Goodreads library import

This directory records the migration from Goodreads into the Git-backed Decap
books collection. The collection itself is the database: every book is one
front-matter-only Markdown file in `_books/`. Files here are import manifests,
research provenance, and resumable processing reports; they are not an
intermediate database used by the website.

The original migration reconciled a complete 1,056-row Goodreads export with
89 existing curated records and added 967 new records. Existing records are
protected, and imported records default to `recommended: false`.

## Data flow

```text
Goodreads CSV
    |
    +-- scripts/import_goodreads.py ----------> _books/*.md
    |                                           _import/goodreads/library.jsonl
    |
    +-- researched synopsis batches
    |      +-- scripts/apply_book_synopses.py -> _books/*.md
    |
    +-- scripts/enrich_book_covers.py --------> assets/covers/*.jpg
                                                _books/*.md (cover and color)
                                                _import/goodreads/covers.jsonl

Jekyll: _books/*.md -> /books/data.json -> books UI
Decap:  _books/*.md <-> browser editor
```

`_pages/books-data.json` serializes the collection during the Jekyll build. The
interactive bookshelf fetches that endpoint and selects only records with
`recommended: true`; non-recommended imports remain available to Decap and to
any catalog UI that consumes the same endpoint.

## Files

| Path | Purpose |
| --- | --- |
| `_books/*.md` | Canonical, Decap-editable book records. |
| `library.jsonl` | One reconciliation row per Goodreads export row, including its target record and whether that record was protected. |
| `synopses/*.jsonl` | Researched synopsis inputs and their source URLs. These preserve provenance after the synopsis is copied into `_books`. |
| `covers.jsonl` | Resumable cover report with status, candidates, dimensions, hashes, selected source, and spine color. |
| `cover-overrides.jsonl` | Manually reviewed cover URLs used when automatic candidates are absent or wrong. |
| `assets/covers/*.jpg` | Normalized local cover files used by the site. |

## Invariants

- The 89 pre-migration records and their covers must not be changed by an
  import or enrichment run.
- Each Goodreads row maps to exactly one record and each imported record has a
  unique numeric `goodreads_id`.
- New Goodreads records are never recommended automatically.
- The importer creates missing records but never rewrites or deletes existing
  records. Subsequent metadata edits belong in Decap or the individual book
  file.
- Cover enrichment may change only `cover` and `color` on an imported record.
- ISBNs are normalized and validated before being used for reconciliation.
- The Goodreads CSV is an input, not a repository artifact. Never commit an
  export containing private Goodreads data.

The collection tests enforce the import count, unique titles, unique ISBNs,
valid record fields, existing cover paths, 967 non-recommended imported books,
and 89 recommended curated books.

## Dependencies

Run commands from the repository root. The examples use `uv` so dependencies
do not need to be installed globally:

```sh
uv run --with pyyaml python scripts/import_goodreads.py --help
uv run --with pyyaml python scripts/apply_book_synopses.py --help
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py --help
```

The same Python packages are listed in `scripts/requirements.txt` for a virtual
environment workflow.

## Importing a Goodreads export

Always begin with a complete Goodreads library export and a clean worktree.
The first command is read-only:

```sh
uv run --with pyyaml python scripts/import_goodreads.py \
  /path/to/goodreads_library_export.csv --dry-run
```

Review the reported matches, additions, statuses, missing ISBNs, and warnings.
Then pin the expected number of additions in the real run:

```sh
uv run --with pyyaml python scripts/import_goodreads.py \
  /path/to/goodreads_library_export.csv --expected-new N
```

For the original migration, `N` was 967. Rerunning the same complete export
against the migrated collection should use `--expected-new 0`. For a later
export, use the addition count reported by the dry run.

The importer is intentionally not a two-way Goodreads synchronization tool. It
does not update the status, tags, dates, or other fields of existing records,
and it does not remove records missing from an export.

## Applying researched synopses

Synopsis files are JSON Lines. Each row contains:

- `goodreads_id`
- `status`: `ready` or `needs_review`
- `synopsis` for ready rows
- one or more source URLs
- an `issues` list

A ready synopsis must be 35–65 words, exactly two sentences, neutral, and
content-focused. Promotional language, reviewer commentary, author biography,
and duplicated synopsis text are rejected by the validator.

Validate one or more batches before applying them:

```sh
uv run --with pyyaml python scripts/apply_book_synopses.py \
  _import/goodreads/synopses/batch-005-a.jsonl \
  _import/goodreads/synopses/batch-005-b.jsonl \
  --dry-run
```

Apply the same validated inputs by removing `--dry-run`:

```sh
uv run --with pyyaml python scripts/apply_book_synopses.py \
  _import/goodreads/synopses/batch-005-a.jsonl \
  _import/goodreads/synopses/batch-005-b.jsonl
```

Applying a completed batch again is safe: records whose synopsis already
matches are left unchanged.

## Enriching covers

Run the built-in checks first:

```sh
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py --self-check
```

A conservative resumable run is:

```sh
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py \
  --resume --workers 4 --delay 0.25
```

Use `--limit N` for a checkpoint-sized batch or `--ids ID [ID ...]` for exact
records. An optional Google Books key enables an additional exact-ISBN source:

```sh
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py \
  --resume --ids 12345 67890 \
  --google-api-key "$GOOGLE_BOOKS_API_KEY"
```

Without a Google key, the script checks reviewed overrides, Open Library by
validated ISBN, and Goodreads by exact Goodreads ID. It verifies the response
type, decodes the image, rejects placeholders and implausible images, enforces
minimum dimensions and aspect ratio, normalizes accepted images to JPEG, and
calculates the spine color. Every result is checkpointed in `covers.jsonl`.

`--resume` skips results that are still valid on disk and retries transient
network failures. It also preserves terminal failures so a long run can be
restarted without repeating settled work.

### Manually reviewed covers

Add one compact JSON object per line to `cover-overrides.jsonl`:

```json
{"goodreads_id":"12345","source_url":"https://publisher.example/cover.jpg","source_page":"https://publisher.example/book","note":"Official publisher cover for the matching edition."}
```

Prefer a publisher or author-controlled page, confirm that the edition/title
matches, and inspect the image directly. For a record currently marked
`no_valid_candidate`, rerun that ID **without** `--resume` so the reviewed
override replaces the terminal report row:

```sh
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py --ids 12345
```

The script deliberately refuses to overwrite an existing destination. To
replace a wrong saved cover, first remove the old generated image and clear the
record's `cover` value, then rerun the exact ID without `--resume`. Inspect the
resulting diff before committing.

## Verification

Run these checks before each checkpoint or merge:

```sh
uv run --with pyyaml --with requests --with pillow \
  python scripts/enrich_book_covers.py --self-check
ruby _tests/books-collection.test.rb
node --test _tests/decap-config.test.mjs
git diff --check
```

Before production, also run the same build Cloudflare Pages runs:

```sh
./build.sh
```

Review the generated `/books/data.json`, open `/books/`, and test creating and
editing a book through Decap.

## Checkpoints and recovery

- Commit and push small, validated checkpoints. A pushed feature branch is a
  backup, but it is not a production deployment.
- `library.jsonl` and `covers.jsonl` are written atomically.
- Cover assets and book records are installed independently, so completed work
  survives an interrupted run.
- After interruption, inspect `git status`, validate any partial synopsis JSONL,
  and restart cover processing with `--resume`.
- Never resolve a conflict by replacing the protected curated records wholesale.

## Production and Decap

Production Decap is configured in `admin/config.yml` to read and write
`ibercovich/blog` on `master`. Cloudflare Pages also deploys the production
branch. Pushing `agent/goodreads-catalog-import` therefore saves the work on
GitHub but does not make its books visible in production Decap.

The release sequence is:

1. Commit all validated records, reports, synopsis batches, covers, scripts,
   and this README on the import branch.
2. Merge the latest `master` into the import branch and resolve conflicts there.
3. Run the verification commands and production build.
4. Merge the import branch into `master` and push `master`.
5. Wait for the Cloudflare Pages deployment, then verify `/books/`,
   `/books/data.json`, and the Decap books collection.
6. Remove the temporary worktree and feature branch only after production is
   verified.
