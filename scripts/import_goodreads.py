#!/usr/bin/env python3
"""Import a Goodreads CSV into the Git-backed books collection.

The importer is deterministic and offline. It creates new records but never
rewrites an existing one. Cover and synopsis enrichment happen separately.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = ROOT / "_books"
MANIFEST_PATH = ROOT / "_import" / "goodreads" / "library.jsonl"
FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
JEKYLL_DATE_LIKE = re.compile(r"\A\d{1,4}-\d{1,2}-\d{1,2}(?:-|\Z)")

STATUS_MAP = {
    "read": "read",
    "to-read": "want_to_read",
    "currently-reading": "currently_reading",
    "tbd": "tbd",
}

# All 89 original curated records were manually reconciled against this
# Goodreads export. Keeping the IDs external preserves those files byte for
# byte while making future reruns independent of ISBN/title edits.
PROTECTED_GOODREADS_IDS = {
    "1067": "1776.md",
    "4069": "mans-search-for-meaning.md",
    "5544": "surely-youre-joking-mr-feynman.md",
    "10631": "sam-walton-made-in-america.md",
    "17994": "the-code-book.md",
    "27539": "on-intelligence.md",
    "29608": "the-codebreakers.md",
    "30659": "meditations.md",
    "41793": "hackers-and-painters.md",
    "51964": "old-mans-war.md",
    "54479": "around-the-world-in-eighty-days.md",
    "69242": "made-to-stick.md",
    "89186": "pushing-ice.md",
    "91360": "devil-take-the-hindmost.md",
    "98233": "founders-at-work.md",
    "101630": "in-the-presence-of-mine-enemies.md",
    "211099": "losing-my-virginity.md",
    "222146": "masters-of-doom.md",
    "242472": "the-black-swan.md",
    "281123": "softwar.md",
    "324735": "eboys.md",
    "324750": "high-output-management.md",
    "341735": "replay.md",
    "373726": "zen-and-the-art-of-motorcycle-maintenance.md",
    "509784": "the-end-of-eternity.md",
    "866140": "incompleteness.md",
    "2054761": "the-snowball.md",
    "3030093": "the-right-stuff.md",
    "4030991": "shoe-dog.md",
    "6480781": "open.md",
    "7081902": "common-sense-on-mutual-funds.md",
    "8032112": "the-big-short.md",
    "9848159": "the-innovators-dilemma.md",
    "9969571": "ready-player-one.md",
    "11084145": "steve-jobs.md",
    "13166586": "the-fish-that-ate-the-whale.md",
    "13453029": "wool-omnibus.md",
    "13530973": "antifragile.md",
    "15870068": "total-recall.md",
    "16059922": "pour-your-heart-into-it.md",
    "17660462": "the-everything-store.md",
    "17707591": "how-to-create-a-mind.md",
    "18007564": "the-martian.md",
    "18077903": "creativity-inc.md",
    "18176747": "the-hard-thing-about-hard-things.md",
    "18774981": "waking-up.md",
    "18839218": "netflixed.md",
    "18894332": "art-of-money-getting.md",
    "20518872": "the-three-body-problem.md",
    "20639917": "flash-boys.md",
    "21480734": "dataclysm.md",
    "22609391": "the-wright-brothers.md",
    "22891356": "the-signal-and-the-noise.md",
    "23168817": "the-dark-forest.md",
    "24984035": "map-and-territory.md",
    "25451264": "deaths-end.md",
    "25816990": "sapiens.md",
    "28186015": "weapons-of-math-destruction.md",
    "29566029": "algorithms-to-live-by.md",
    "29965800": "the-subtle-art-of-not-giving-a-fck.md",
    "30268520": "superforecasting.md",
    "34941133": "principles.md",
    "34981875": "self-reliance.md",
    "35540648": "how-to-actually-change-your-mind.md",
    "36556202": "the-coddling-of-the-american-mind.md",
    "36613747": "how-to-change-your-mind.md",
    "37653154": "zero-to-one.md",
    "38799469": "bad-blood.md",
    "40242274": "a-random-walk-down-wall-street.md",
    "40538681": "midnight-in-chernobyl.md",
    "40725112": "vaccinated.md",
    "42900232": "deep-learning-with-keras.md",
    "43172337": "enlightenment-now.md",
    "43720168": "winter-world.md",
    "43889703": "the-man-who-solved-the-market.md",
    "44164651": "the-solar-war.md",
    "44525305": "the-ride-of-a-lifetime.md",
    "44678031": "yearbook.md",
    "45416671": "a-short-history-of-nearly-everything.md",
    "46223297": "permanent-record.md",
    "52880778": "red-rising.md",
    "54493401": "project-hail-mary.md",
    "54898389": "the-almanack-of-naval-ravikant.md",
    "54968118": "the-code-breaker.md",
    "56146394": "slate-star-codex-essays.md",
    "122765395": "elon-musk.md",
    "202102017": "gray-matters.md",
    "205307264": "boom.md",
    "239472387": "the-scaling-era.md",
}

AUTHOR_OVERRIDES = {"Liu Cixin": "Liu, Cixin"}

# Goodreads 112974860 is explicitly the Kindle edition. Its ISBN-10 column
# names the hardcover while ISBN13 names the ebook, so retain the edition the
# export identifies instead of guessing when the two identifiers conflict.
ISBN_OVERRIDES = {"112974860": "9780593230084"}


@dataclass(frozen=True)
class BookFile:
    path: Path
    data: dict
    source: bytes


def clean_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def unwrap_goodreads_number(value: str | None) -> str:
    value = (value or "").strip()
    match = re.fullmatch(r'=\s*"(.*)"', value)
    return match.group(1) if match else value


def isbn10_is_valid(value: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dX]", value):
        return False
    digits = [int(char) for char in value[:9]]
    check = 10 if value[-1] == "X" else int(value[-1])
    return (sum((10 - i) * digit for i, digit in enumerate(digits)) + check) % 11 == 0


def isbn13_is_valid(value: str) -> bool:
    if not re.fullmatch(r"(?:978|979)\d{10}", value):
        return False
    total = sum(
        int(char) * (1 if index % 2 == 0 else 3)
        for index, char in enumerate(value[:12])
    )
    return (10 - total % 10) % 10 == int(value[-1])


def normalize_isbn(value: str | None) -> str:
    value = re.sub(r"[^0-9X]", "", unwrap_goodreads_number(value).upper())
    return value if isbn10_is_valid(value) or isbn13_is_valid(value) else ""


def isbn10_to_isbn13(value: str) -> str:
    stem = f"978{value[:9]}"
    total = sum(
        int(char) * (1 if index % 2 == 0 else 3)
        for index, char in enumerate(stem)
    )
    return f"{stem}{(10 - total % 10) % 10}"


def isbn_equivalents(value: str | None) -> set[str]:
    value = normalize_isbn(value)
    if not value:
        return set()
    return {value, isbn10_to_isbn13(value)} if len(value) == 10 else {value}


def canonical_isbn(value: str | None) -> str:
    value = normalize_isbn(value)
    return isbn10_to_isbn13(value) if len(value) == 10 else value


def source_isbn(row: dict[str, str]) -> tuple[str, list[str]]:
    values = []
    warnings = []
    for column in ("ISBN13", "ISBN"):
        raw = unwrap_goodreads_number(row.get(column)).strip()
        value = normalize_isbn(raw)
        if raw and not value:
            warnings.append(f"{column} contains invalid identifier {raw!r}; omitting it")
        elif value:
            values.append((column, value))
            expected = 13 if column == "ISBN13" else 10
            if len(value) != expected:
                warnings.append(f"{column} contains ISBN-{len(value)} {value}")
    override = ISBN_OVERRIDES.get(clean_text(row.get("Book Id")))
    if override:
        if override not in {value for _column, value in values}:
            raise ValueError(f"reviewed ISBN override {override} is absent from the source row")
        warnings.append(f"using reviewed edition ISBN override {override}")
        return override, warnings

    canonical_values = {canonical_isbn(value) for _column, value in values}
    if len(canonical_values) > 1:
        rendered = ", ".join(value for _column, value in values)
        raise ValueError(
            f"Goodreads {row['Book Id']} contains conflicting valid ISBNs: {rendered}"
        )
    isbn13 = next((value for _column, value in values if len(value) == 13), "")
    isbn10 = next((value for _column, value in values if len(value) == 10), "")
    return isbn13 or isbn10, warnings


def slugify(value: str, limit: int = 170) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "book"
    if JEKYLL_DATE_LIKE.match(slug):
        slug = f"book-{slug}"
    return slug[:limit].rstrip("-")


def read_books() -> list[BookFile]:
    result = []
    for path in sorted(BOOKS_DIR.glob("*.md")):
        source = path.read_bytes()
        match = FRONT_MATTER_RE.match(source.decode("utf-8"))
        if not match:
            raise ValueError(f"{path} has invalid YAML front matter")
        data = yaml.safe_load(match.group(1)) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} front matter must be a mapping")
        result.append(BookFile(path, data, source))
    return result


def author_for(row: dict[str, str]) -> str:
    raw = clean_text(row.get("Author"))
    return AUTHOR_OVERRIDES.get(raw, clean_text(row.get("Author l-f")) or raw)


def identity_words(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", value.casefold())


def identity_matches(row: dict[str, str], book: BookFile) -> bool:
    title_matches = identity_words(clean_text(row.get("Title"))) == identity_words(
        str(book.data.get("title") or "")
    )
    source_author = sorted(identity_words(author_for(row)))
    target_author = sorted(identity_words(str(book.data.get("author") or "")))
    return title_matches and source_author == target_author


def collections_for(row: dict[str, str]) -> list[str]:
    reserved = {clean_text(row.get("Exclusive Shelf")).casefold(), "recommended"}
    values = {
        clean_text(item)
        for item in (row.get("Bookshelves") or "").split(",")
        if clean_text(item) and clean_text(item).casefold() not in reserved
    }
    return sorted(values, key=str.casefold)


def source_date_read(row: dict[str, str]) -> str | None:
    value = (row.get("Date Read") or "").strip()
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y/%m/%d").date().isoformat()
    except ValueError as error:
        raise ValueError(f"invalid Date Read {value!r} for Goodreads {row['Book Id']}") from error


def finished_on(row: dict[str, str]) -> str | None:
    shelf = clean_text(row.get("Exclusive Shelf"))
    return source_date_read(row) if STATUS_MAP.get(shelf) == "read" else None


def data_for(row: dict[str, str], isbn: str) -> dict:
    shelf = clean_text(row.get("Exclusive Shelf"))
    if shelf not in STATUS_MAP:
        raise ValueError(f"unknown Exclusive Shelf {shelf!r} for Goodreads {row['Book Id']}")
    owned = clean_text(row.get("Owned Copies")) or "0"
    if not owned.isdigit():
        raise ValueError(f"invalid Owned Copies {owned!r} for Goodreads {row['Book Id']}")
    data = {
        "title": clean_text(row.get("Title")),
        "author": author_for(row),
        "goodreads_id": clean_text(row.get("Book Id")),
    }
    if isbn:
        data["isbn"] = isbn
    data.update(
        {
            "cover": "",
            "color": "#6B4C3B",
            "status": STATUS_MAP[shelf],
            "collections": collections_for(row),
            "physical_copy": int(owned) > 0,
            "recommended": False,
        }
    )
    date = finished_on(row)
    if date:
        data["finished_on"] = date
    data["synopsis"] = ""
    return data


def render_book(data: dict) -> bytes:
    front = yaml.safe_dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    ).rstrip()
    return f"---\n{front}\n---\n".encode()


def atomic_write(path: Path, source: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(source)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_manifest(rows: list[dict]) -> None:
    source = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
    atomic_write(MANIFEST_PATH, source)


def run(csv_path: Path, dry_run: bool, expected_new: int | None) -> None:
    existing = read_books()
    originals = {book.path: book.source for book in existing}
    by_name = {book.path.name: book for book in existing}
    by_goodreads = {}
    by_isbn: dict[str, list[BookFile]] = defaultdict(list)
    title_keys = set()
    for book in existing:
        goodreads_id = str(book.data.get("goodreads_id") or "")
        if goodreads_id:
            if goodreads_id in by_goodreads:
                raise ValueError(f"duplicate goodreads_id {goodreads_id}")
            by_goodreads[goodreads_id] = book
        raw_isbn = str(book.data.get("isbn") or "").strip()
        if raw_isbn and not normalize_isbn(raw_isbn):
            raise ValueError(f"{book.path} contains invalid ISBN {raw_isbn!r}")
        for key in isbn_equivalents(raw_isbn):
            by_isbn[key].append(book)
        title_keys.add(clean_text(str(book.data.get("title") or "")).casefold())

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "Book Id", "Title", "Author", "Author l-f", "ISBN", "ISBN13",
            "Exclusive Shelf", "Bookshelves", "Date Read", "Owned Copies",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    ids = [clean_text(row.get("Book Id")) for row in rows]
    duplicate_ids = [key for key, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"duplicate Goodreads IDs: {', '.join(sorted(duplicate_ids))}")

    parsed_isbns = {}
    source_isbn_ids = {}
    preflight_warnings = []
    for row in rows:
        goodreads_id = clean_text(row.get("Book Id"))
        isbn, row_warnings = source_isbn(row)
        parsed_isbns[goodreads_id] = isbn
        preflight_warnings.extend(
            f"Goodreads {goodreads_id}: {warning}" for warning in row_warnings
        )
        canonical = canonical_isbn(isbn)
        if canonical and canonical in source_isbn_ids:
            raise ValueError(
                f"duplicate source ISBN {canonical}: Goodreads "
                f"{source_isbn_ids[canonical]} and {goodreads_id}"
            )
        if canonical:
            source_isbn_ids[canonical] = goodreads_id

    additions = []
    matches = []
    warnings = preflight_warnings
    manifest = []
    planned_paths = set(by_name)
    planned_titles = set(title_keys)

    for row in rows:
        goodreads_id = clean_text(row.get("Book Id"))
        if not goodreads_id.isdigit():
            raise ValueError(f"invalid Goodreads ID {goodreads_id!r}")
        isbn = parsed_isbns[goodreads_id]

        protected_name = PROTECTED_GOODREADS_IDS.get(goodreads_id)
        if protected_name:
            if protected_name not in by_name:
                raise ValueError(f"protected mapping points to missing {protected_name}")
            target = by_name[protected_name]
            matches.append((goodreads_id, "protected_id", target))
        elif goodreads_id in by_goodreads:
            target = by_goodreads[goodreads_id]
            matches.append((goodreads_id, "goodreads_id", target))
        else:
            candidates = {
                book.path: book
                for key in isbn_equivalents(isbn)
                for book in by_isbn.get(key, [])
            }
            if len(candidates) > 1:
                raise ValueError(f"Goodreads {goodreads_id} ISBN matches multiple records")
            if candidates:
                target = next(iter(candidates.values()))
                target_id = str(target.data.get("goodreads_id") or "")
                if target_id and target_id != goodreads_id:
                    raise ValueError(
                        f"Goodreads {goodreads_id} ISBN is already assigned to "
                        f"Goodreads {target_id} in {target.path}"
                    )
                if not identity_matches(row, target):
                    raise ValueError(
                        f"Goodreads {goodreads_id} ISBN matches {target.path}, "
                        "but title/author do not; add an explicit reviewed mapping"
                    )
                matches.append((goodreads_id, "isbn", target))
            else:
                data = data_for(row, isbn)
                title_key = data["title"].casefold()
                if title_key in planned_titles:
                    raise ValueError(f"duplicate title would be created: {data['title']!r}")
                planned_titles.add(title_key)
                stem = f"{slugify(data['title'])}-gr-{goodreads_id}"
                path = BOOKS_DIR / f"{stem}.md"
                if path.name in planned_paths:
                    raise ValueError(f"duplicate path would be created: {path.name}")
                planned_paths.add(path.name)
                additions.append((path, data))
                target = BookFile(path, data, b"")
                by_goodreads[goodreads_id] = target
                for key in isbn_equivalents(isbn):
                    by_isbn[key].append(target)

        manifest.append(
            {
                "goodreads_id": goodreads_id,
                "record": str(target.path.relative_to(ROOT)),
                "protected": bool(protected_name),
                "source": {
                    "title": clean_text(row.get("Title")),
                    "author": author_for(row),
                    "isbn": isbn or None,
                    "status": STATUS_MAP[clean_text(row.get("Exclusive Shelf"))],
                    "collections": collections_for(row),
                    "physical_copy": int(clean_text(row.get("Owned Copies")) or "0") > 0,
                    "date_read": source_date_read(row),
                },
            }
        )

    if expected_new is not None and len(additions) != expected_new:
        raise ValueError(f"expected {expected_new} new books, reconciled {len(additions)}")

    if not dry_run:
        for path, data in additions:
            atomic_write(path, render_book(data))
        write_manifest(manifest)

    changed = [path for path, source in originals.items() if path.read_bytes() != source]
    if changed:
        raise RuntimeError(f"existing records changed: {', '.join(map(str, changed))}")

    methods = Counter(method for _gid, method, _book in matches)
    statuses = Counter(data["status"] for _path, data in additions)
    verb = "Would add" if dry_run else "Added"
    print(f"{verb} {len(additions)} books; preserved {len(matches)} existing books.")
    print("Existing matches: " + ", ".join(f"{key}={methods[key]}" for key in sorted(methods)))
    print("New statuses: " + ", ".join(f"{key}={statuses[key]}" for key in sorted(statuses)))
    print(f"New books without ISBN: {sum('isbn' not in data for _path, data in additions)}")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  {warning}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csvfile", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expected-new", type=int)
    args = parser.parse_args()
    run(args.csvfile.expanduser().resolve(), args.dry_run, args.expected_new)


if __name__ == "__main__":
    main()
