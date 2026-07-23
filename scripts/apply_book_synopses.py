#!/usr/bin/env python3
"""Validate researched synopsis JSONL and apply ready results to imported books."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from import_goodreads import atomic_write, read_books, render_book


BANNED = re.compile(
    r"\b(?:acclaimed|award[- ]winning|best[- ]selling|bestseller|must[- ]read|"
    r"masterpiece|groundbreaking|definitive|seminal|compelling|riveting|"
    r"fascinating|remarkable|extraordinary|essential|critics?|reviewers?|"
    r"fans of|readers will)\b",
    re.IGNORECASE,
)


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", value, re.UNICODE))


def split_sentences(value: str) -> list[str]:
    protected = re.sub(r"\b([A-Z])\.", r"\1<dot>", value)
    protected = re.sub(
        r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|U\.S|U\.K)\.",
        lambda match: match.group(0).replace(".", "<dot>"),
        protected,
        flags=re.IGNORECASE,
    )
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", protected)
    return [part.replace("<dot>", ".").strip() for part in parts if part.strip()]


def validate_result(record: dict, known_ids: set[str]) -> tuple[str, str] | None:
    goodreads_id = str(record.get("goodreads_id") or "")
    if goodreads_id not in known_ids:
        raise ValueError(f"unknown imported goodreads_id {goodreads_id!r}")
    status = record.get("status")
    if status not in {"ready", "needs_review"}:
        raise ValueError(f"Goodreads {goodreads_id}: invalid status {status!r}")
    if status == "needs_review":
        if not record.get("issues"):
            raise ValueError(f"Goodreads {goodreads_id}: needs_review requires issues")
        return None

    synopsis = record.get("synopsis")
    if not isinstance(synopsis, str):
        raise ValueError(f"Goodreads {goodreads_id}: ready result needs a synopsis")
    normalized = " ".join(synopsis.split())
    if normalized != synopsis:
        raise ValueError(f"Goodreads {goodreads_id}: synopsis whitespace is not normalized")
    words = word_count(synopsis)
    if not 35 <= words <= 65:
        raise ValueError(f"Goodreads {goodreads_id}: synopsis has {words} words, expected 35-65")
    sentences = split_sentences(synopsis)
    if len(sentences) != 2 or not all(sentence[-1:] in ".!?" for sentence in sentences):
        raise ValueError(f"Goodreads {goodreads_id}: synopsis must be exactly two sentences")
    match = BANNED.search(synopsis)
    if match:
        raise ValueError(
            f"Goodreads {goodreads_id}: banned promotional language {match.group(0)!r}"
        )
    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"Goodreads {goodreads_id}: at least one source is required")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError(f"Goodreads {goodreads_id}: malformed source")
        parsed = urlparse(str(source.get("url") or ""))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Goodreads {goodreads_id}: invalid source URL")
    return goodreads_id, synopsis


def load_results(paths: list[Path]) -> list[dict]:
    results = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            results.append(record)
    return results


def run(paths: list[Path], dry_run: bool) -> None:
    books = {
        str(book.data.get("goodreads_id")): book
        for book in read_books()
        if book.data.get("goodreads_id")
    }
    results = load_results(paths)
    seen = set()
    ready = []
    review = 0
    for record in results:
        goodreads_id = str(record.get("goodreads_id") or "")
        if goodreads_id in seen:
            raise ValueError(f"duplicate synopsis result for Goodreads {goodreads_id}")
        seen.add(goodreads_id)
        validated = validate_result(record, set(books))
        if validated:
            ready.append(validated)
        else:
            review += 1

    existing_owners: dict[str, set[str]] = {}
    for goodreads_id, book in books.items():
        synopsis = str(book.data.get("synopsis") or "")
        if synopsis.strip():
            existing_owners.setdefault(synopsis, set()).add(goodreads_id)
    duplicates = [
        synopsis
        for goodreads_id, synopsis in ready
        if existing_owners.get(synopsis, set()) - {goodreads_id}
    ]
    if duplicates or len({synopsis for _goodreads_id, synopsis in ready}) != len(ready):
        raise ValueError("duplicate synopsis text detected")

    changed = 0
    if not dry_run:
        for goodreads_id, synopsis in ready:
            book = books[goodreads_id]
            if book.data.get("synopsis") == synopsis:
                continue
            book.data["synopsis"] = synopsis
            atomic_write(book.path, render_book(book.data))
            changed += 1
    action = "Would apply" if dry_run else "Applied"
    print(f"{action} {len(ready) if dry_run else changed} synopses; {review} need review.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run([path.expanduser().resolve() for path in args.results], args.dry_run)


if __name__ == "__main__":
    main()
