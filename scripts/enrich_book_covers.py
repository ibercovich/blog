#!/usr/bin/env python3
"""Safely enrich Goodreads-imported books with validated cover images."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import re
import tempfile
import time
import warnings
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, ImageDraw, ImageOps, ImageStat, UnidentifiedImageError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from import_books import (
    BLOG_ROOT,
    COVERS_DIR,
    extract_dominant_color,
    load_existing_books,
    write_book_file,
)


REPORT_PATH = BLOG_ROOT / "_import" / "goodreads" / "covers.jsonl"
MIN_WIDTH, MIN_HEIGHT = 200, 280
PREFERRED_WIDTH, PREFERRED_HEIGHT = 300, 450
MIN_ASPECT, MAX_ASPECT = 0.35, 1.05
MAX_BYTES, MAX_PIXELS = 10 * 1024 * 1024, 25_000_000
DEFAULT_COLOR = "#6B4C3B"
PLACEHOLDER_MARKERS = (
    "nophoto",
    "nocover",
    "no-cover",
    "no_image",
    "no-image",
    "book-default",
    "default-book",
    "missing-cover",
    "/default/",
)
TERMINAL_STATUSES = {
    "saved",
    "already_has_cover",
    "no_valid_candidate",
    "conflict_existing_destination",
}
RETRYABLE_REASON_MARKERS = (
    "http_202",
    "http_429",
    "http_500",
    "http_502",
    "http_503",
    "http_504",
    "request_error",
    "empty_response",
)


class FetchError(RuntimeError):
    pass


class GoodreadsMetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.identity_urls = []
        self.image_urls = []

    def handle_starttag(self, tag, attrs):
        values = {str(key).casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "meta":
            name = (values.get("property") or values.get("name") or "").casefold()
            content = values.get("content", "").strip()
            if name in {"og:image", "og:image:secure_url"} and content:
                self.image_urls.append(content)
            elif name == "og:url" and content:
                self.identity_urls.append(content)
        elif tag.casefold() == "link":
            rel = {part.casefold() for part in values.get("rel", "").split()}
            if "canonical" in rel and values.get("href"):
                self.identity_urls.append(values["href"].strip())


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_isbn(value):
    return re.sub(r"[^0-9X]", "", str(value or "").upper())


def valid_isbn10(value):
    if not re.fullmatch(r"\d{9}[\dX]", value):
        return False
    check = 10 if value[-1] == "X" else int(value[-1])
    return (sum((10 - i) * int(d) for i, d in enumerate(value[:9])) + check) % 11 == 0


def valid_isbn13(value):
    if not re.fullmatch(r"(?:978|979)\d{10}", value):
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(value[:12]))
    return (10 - total % 10) % 10 == int(value[-1])


def canonical_isbn(value):
    value = normalize_isbn(value)
    if valid_isbn13(value):
        return value
    if not valid_isbn10(value):
        return ""
    stem = "978" + value[:9]
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(stem))
    return stem + str((10 - total % 10) % 10)


def isbn_equivalents(value):
    value = normalize_isbn(value)
    canonical = canonical_isbn(value)
    return {value, canonical} if canonical else set()


def is_http_url(value):
    parsed = urlparse(value)
    return parsed.scheme.casefold() in {"http", "https"} and bool(parsed.netloc)


def placeholder_url(value):
    folded = value.casefold()
    return any(marker in folded for marker in PLACEHOLDER_MARKERS)


def goodreads_url_has_id(value, goodreads_id):
    return re.search(
        rf"/book/show/{re.escape(goodreads_id)}(?:[._-]|$)",
        urlparse(value).path,
    ) is not None


def build_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        # Goodreads sometimes throttles public book pages with an empty 202
        # response instead of 429. Retrying it respects Retry-After when sent.
        status_forcelist=(202, 429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = (
        "ivanbercovich.com-book-cover-import/1.0 (personal library maintenance)"
    )
    return session


def fetch_bytes(session, url, max_bytes=MAX_BYTES, params=None):
    if not is_http_url(url):
        raise FetchError("invalid_url")
    try:
        with session.get(
            url,
            params=params,
            stream=True,
            timeout=(5, 20),
            allow_redirects=True,
        ) as response:
            if response.status_code != 200:
                raise FetchError(f"http_{response.status_code}")
            length = response.headers.get("content-length", "")
            if length.isdigit() and int(length) > max_bytes:
                raise FetchError("response_too_large")
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise FetchError("response_too_large")
                chunks.append(chunk)
            if not chunks:
                raise FetchError("empty_response")
            mime = response.headers.get("content-type", "").split(";", 1)[0].casefold()
            return b"".join(chunks), mime, response.url
    except FetchError:
        raise
    except requests.RequestException as error:
        raise FetchError(f"request_error:{error.__class__.__name__}") from error


def candidate(source, url, lookup_url, source_id=None):
    result = {"source": source, "source_url": url, "lookup_url": lookup_url}
    if source_id:
        result["source_id"] = source_id
    return result


def discover_open_library(isbn):
    value = normalize_isbn(isbn)
    if not canonical_isbn(value):
        return [], ["open_library:missing_or_invalid_isbn"]
    url = f"https://covers.openlibrary.org/b/isbn/{value}-L.jpg?default=false"
    return [candidate("open_library", url, url, value)], []


def discover_goodreads(session, goodreads_id):
    lookup = f"https://www.goodreads.com/book/show/{goodreads_id}"
    try:
        data, mime, final_url = fetch_bytes(session, lookup, 3 * 1024 * 1024)
    except FetchError as error:
        return [], [f"goodreads:{error}"]
    if mime and mime not in {"text/html", "application/xhtml+xml"}:
        return [], [f"goodreads:unexpected_mime:{mime}"]
    parser = GoodreadsMetaParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    if not any(
        goodreads_url_has_id(url, goodreads_id)
        for url in [final_url, *parser.identity_urls]
    ):
        return [], ["goodreads:identity_mismatch"]
    found, seen = [], set()
    for raw_url in parser.image_urls:
        url = urljoin(final_url, raw_url).replace("http://", "https://", 1)
        if is_http_url(url) and url not in seen:
            seen.add(url)
            found.append(candidate("goodreads", url, lookup, goodreads_id))
    return found, ([] if found else ["goodreads:no_og_image"])


def discover_google(session, isbn, api_key):
    if not api_key:
        return [], []
    equivalents = isbn_equivalents(isbn)
    if not equivalents:
        return [], ["google_books:missing_or_invalid_isbn"]
    try:
        data, mime, _ = fetch_bytes(
            session,
            "https://www.googleapis.com/books/v1/volumes",
            3 * 1024 * 1024,
            {
                "q": f"isbn:{normalize_isbn(isbn)}",
                "maxResults": 5,
                "key": api_key,
            },
        )
    except FetchError as error:
        return [], [f"google_books:{error}"]
    if mime and "json" not in mime:
        return [], [f"google_books:unexpected_mime:{mime}"]
    try:
        payload = json.loads(data)
    except ValueError:
        return [], ["google_books:invalid_json"]
    found, seen = [], set()
    for item in payload.get("items", []):
        info = item.get("volumeInfo") or {}
        provider_ids = {
            normalize_isbn(value.get("identifier"))
            for value in info.get("industryIdentifiers", [])
        }
        provider_canonical = {canonical_isbn(value) for value in provider_ids}
        if not (
            equivalents & provider_ids
            or canonical_isbn(isbn) in provider_canonical
        ):
            continue
        links = info.get("imageLinks") or {}
        url = next(
            (
                links[key]
                for key in ("extraLarge", "large", "medium", "small", "thumbnail")
                if links.get(key)
            ),
            "",
        )
        url = str(url).replace("http://", "https://", 1).replace("&edge=curl", "")
        if is_http_url(url) and url not in seen:
            seen.add(url)
            found.append(
                candidate(
                    "google_books",
                    url,
                    "https://www.googleapis.com/books/v1/volumes",
                    str(item.get("id") or ""),
                )
            )
    return found, ([] if found else ["google_books:no_exact_isbn_image"])


def discover_candidates(session, book, api_key):
    found, issues = [], []
    for lookup in (
        lambda: discover_open_library(book.data.get("isbn")),
        lambda: discover_goodreads(session, str(book.data["goodreads_id"]).strip()),
        lambda: discover_google(session, book.data.get("isbn"), api_key),
    ):
        candidates, errors = lookup()
        found.extend(candidates)
        issues.extend(errors)
    unique, seen = [], set()
    for item in found:
        if item["source_url"] not in seen:
            seen.add(item["source_url"])
            unique.append(item)
    return unique, issues


def quality_metrics(image):
    preview = ImageOps.grayscale(image.convert("RGB"))
    preview.thumbnail((64, 64), Image.Resampling.LANCZOS)
    histogram = preview.histogram()
    total = sum(histogram) or 1
    extrema = preview.getextrema()
    metrics = {
        "entropy": round(float(preview.entropy()), 3),
        "grayscale_stddev": round(float(ImageStat.Stat(preview).stddev[0]), 3),
        "tonal_range": int(extrema[1] - extrema[0]),
        "white_ratio": round(sum(histogram[248:]) / total, 5),
        "black_ratio": round(sum(histogram[:8]) / total, 5),
    }
    reasons = []
    if (
        metrics["tonal_range"] < 8
        or metrics["grayscale_stddev"] < 3
        or metrics["entropy"] < 1
    ):
        reasons.append("blank_or_nearly_blank")
    if metrics["white_ratio"] > 0.985:
        reasons.append("nearly_all_white")
    if metrics["black_ratio"] > 0.985:
        reasons.append("nearly_all_black")
    if metrics["white_ratio"] > 0.90 and metrics["entropy"] < 2.5:
        reasons.append("mostly_white_low_detail")
    return reasons, metrics


def to_rgb(image):
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def inspect_image(data, mime, source_url):
    result = {
        "status": "rejected",
        "mime": mime or None,
        "source_bytes": len(data),
        "source_sha256": sha256(data),
        "reasons": [],
    }
    if not mime:
        result["reasons"].append("missing_mime")
    elif not mime.startswith("image/"):
        result["reasons"].append(f"non_image_mime:{mime}")
    if placeholder_url(source_url):
        result["reasons"].append("placeholder_url")
    if result["reasons"]:
        return result, None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                image_format = probe.format
                probe.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.seek(0)
                decoded.load()
                image = ImageOps.exif_transpose(decoded).copy()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        result["reasons"].append("decompression_bomb")
        return result, None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        result["reasons"].append("decode_error")
        return result, None
    width, height = image.size
    aspect = width / height if height else math.inf
    result.update(
        {
            "format": image_format,
            "width": width,
            "height": height,
            "pixel_area": width * height,
            "aspect_ratio": round(aspect, 5),
            "preferred_dimensions": width >= PREFERRED_WIDTH
            and height >= PREFERRED_HEIGHT,
        }
    )
    if width * height > MAX_PIXELS:
        result["reasons"].append("too_many_pixels")
    if width < MIN_WIDTH:
        result["reasons"].append(f"width_below_{MIN_WIDTH}")
    if height < MIN_HEIGHT:
        result["reasons"].append(f"height_below_{MIN_HEIGHT}")
    if not MIN_ASPECT <= aspect <= MAX_ASPECT:
        result["reasons"].append("aspect_ratio_out_of_range")
    blank_reasons, metrics = quality_metrics(image)
    result["reasons"].extend(blank_reasons)
    result["quality_metrics"] = metrics
    if result["reasons"]:
        return result, None
    normalized_image = to_rgb(image)
    normalized_image.thumbnail((900, 1200), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    normalized_image.save(
        output,
        format="JPEG",
        quality=87,
        optimize=True,
        progressive=True,
    )
    normalized = output.getvalue()
    result.update(
        {
            "status": "valid",
            "normalized_width": normalized_image.width,
            "normalized_height": normalized_image.height,
            "normalized_bytes": len(normalized),
            "sha256": sha256(normalized),
        }
    )
    return result, normalized


def inspect_candidate(session, item):
    report = dict(item)
    if placeholder_url(item["source_url"]):
        report.update(status="rejected", reasons=["placeholder_url"])
        return report, None
    try:
        data, mime, resolved = fetch_bytes(session, item["source_url"])
    except FetchError as error:
        report.update(status="rejected", reasons=[str(error)])
        return report, None
    inspection, normalized = inspect_image(data, mime, resolved)
    report["resolved_url"] = resolved
    report.update(inspection)
    return report, normalized


def select_best(inspected):
    valid = [
        pair
        for pair in inspected
        if pair[0].get("status") == "valid" and pair[1] is not None
    ]
    if not valid:
        return None
    largest_area = max(pair[0]["pixel_area"] for pair in valid)
    # Near-equivalent Goodreads images are usually clean retail covers; Open
    # Library scans can contain library stickers or title pages. Preserve area
    # as the primary threshold, then prefer the cleaner source within 15%.
    near_largest = [
        pair for pair in valid if pair[0]["pixel_area"] >= largest_area * 0.85
    ]
    source_priority = {"goodreads": 3, "google_books": 2, "open_library": 1}
    return max(
        near_largest,
        key=lambda pair: (
            source_priority.get(pair[0].get("source"), 0),
            pair[0]["pixel_area"],
        ),
    )


def load_report():
    if not REPORT_PATH.exists():
        return {}
    entries = {}
    for number, line in enumerate(REPORT_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{REPORT_PATH}:{number} contains invalid JSON") from error
        goodreads_id = str(entry.get("goodreads_id") or "")
        if not goodreads_id.isdigit() or goodreads_id in entries:
            raise ValueError(f"{REPORT_PATH}:{number} has invalid/duplicate goodreads_id")
        entries[goodreads_id] = entry
    return entries


def write_report(entries):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        entries.values(),
        key=lambda item: (str(item.get("record") or ""), int(item["goodreads_id"])),
    )
    data = "".join(
        json.dumps(item, ensure_ascii=False) + "\n"
        for item in ordered
    ).encode()
    temporary = REPORT_PATH.with_name(f".{REPORT_PATH.name}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(REPORT_PATH)
    finally:
        temporary.unlink(missing_ok=True)


def local_cover_path(value):
    value = str(value or "").strip()
    if not value or is_http_url(value):
        return None
    path = (BLOG_ROOT / value.lstrip("/")).resolve()
    try:
        path.relative_to(BLOG_ROOT.resolve())
    except ValueError:
        return None
    return path


def snapshot_protected(books):
    records, covers = {}, {}
    for book in books:
        if str(book.data.get("goodreads_id") or "").strip():
            continue
        records[book.path] = file_sha256(book.path)
        cover = local_cover_path(book.data.get("cover"))
        if cover and cover not in covers:
            covers[cover] = (
                cover.exists(),
                file_sha256(cover) if cover.exists() else None,
            )
    return records, covers


def assert_protected_unchanged(snapshot):
    records, covers = snapshot
    for path, expected in records.items():
        if not path.exists() or file_sha256(path) != expected:
            raise RuntimeError(f"protected record changed: {path}")
    for path, (existed, expected) in covers.items():
        if path.exists() != existed:
            raise RuntimeError(f"protected cover existence changed: {path}")
        if existed and file_sha256(path) != expected:
            raise RuntimeError(f"protected cover changed: {path}")


def destination_for(book):
    filename = f"{book.path.stem}.jpg"
    return f"/assets/covers/{filename}", COVERS_DIR / filename


def install_cover(book, original_record, normalized, color):
    if not str(book.data.get("goodreads_id") or "").strip():
        raise RuntimeError(f"refusing to update protected record {book.path}")
    if str(book.data.get("cover") or "").strip():
        raise RuntimeError(f"record already has a cover: {book.path}")
    if book.path.read_bytes() != original_record:
        raise RuntimeError(f"record changed concurrently: {book.path}")
    public_path, destination = destination_for(book)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    before = copy.deepcopy(book.data)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    installed = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(normalized)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.link(temporary, destination)
        installed = True
        book.data["cover"] = public_path
        book.data["color"] = color
        changed = {
            key
            for key in set(before) | set(book.data)
            if before.get(key) != book.data.get(key)
        }
        if changed - {"cover", "color"}:
            raise RuntimeError(f"unexpected metadata changes: {sorted(changed)}")
        if not write_book_file(book):
            raise RuntimeError("record update unexpectedly produced no change")
    except Exception:
        book.data.clear()
        book.data.update(before)
        if installed and destination.exists() and file_sha256(destination) == sha256(normalized):
            destination.unlink()
        raise
    finally:
        temporary.unlink(missing_ok=True)
    return public_path, destination


def result_base(book):
    return {
        "goodreads_id": str(book.data["goodreads_id"]).strip(),
        "record": str(book.path.relative_to(BLOG_ROOT)),
        "title": str(book.data.get("title") or ""),
        "isbn": normalize_isbn(book.data.get("isbn")) or None,
        "updated_at": now(),
    }


def resume_current(book, entry, dry_run):
    status = str(entry.get("status") or "")
    if status == "would_save":
        return dry_run
    if status not in TERMINAL_STATUSES:
        return False
    if status == "saved":
        cover = local_cover_path(book.data.get("cover"))
        return bool(
            str(book.data.get("cover") or "") == str(entry.get("cover") or "")
            and cover
            and cover.exists()
            and entry.get("sha256")
            and file_sha256(cover) == entry["sha256"]
        )
    if status == "already_has_cover":
        return bool(str(book.data.get("cover") or "").strip())
    if status == "conflict_existing_destination":
        return destination_for(book)[1].exists()
    if status == "no_valid_candidate":
        reasons = [str(reason) for reason in entry.get("reasons") or []]
        return not any(
            marker in reason
            for reason in reasons
            for marker in RETRYABLE_REASON_MARKERS
        )
    return True


def process_book(session, book, original_record, api_key, dry_run):
    result = result_base(book)
    if str(book.data.get("cover") or "").strip():
        result.update(
            status="already_has_cover",
            cover=str(book.data["cover"]),
            reasons=[],
            candidates=[],
        )
        return result
    public_path, destination = destination_for(book)
    if destination.exists():
        result.update(
            status="conflict_existing_destination",
            cover=public_path,
            reasons=["destination_exists_but_record_cover_is_empty"],
            candidates=[],
        )
        return result
    candidates, lookup_issues = discover_candidates(session, book, api_key)
    inspected = [inspect_candidate(session, item) for item in candidates]
    safe_candidates = [item for item, _ in inspected]
    best = select_best(inspected)
    if not best:
        reasons = lookup_issues + [
            reason
            for item in safe_candidates
            for reason in item.get("reasons", [])
        ]
        result.update(
            status="no_valid_candidate",
            reasons=list(dict.fromkeys(reasons)) or ["no_candidates"],
            candidates=safe_candidates,
        )
        return result
    selected, normalized = best
    color = (extract_dominant_color(normalized) or DEFAULT_COLOR).upper()
    result.update(
        status="would_save" if dry_run else "selected",
        source=selected["source"],
        source_url=selected["source_url"],
        resolved_url=selected.get("resolved_url"),
        width=selected["width"],
        height=selected["height"],
        normalized_width=selected["normalized_width"],
        normalized_height=selected["normalized_height"],
        source_sha256=selected["source_sha256"],
        sha256=selected["sha256"],
        color=color,
        cover=public_path,
        reasons=[],
        candidates=safe_candidates,
    )
    if not dry_run:
        installed_path, installed_file = install_cover(
            book, original_record, normalized, color
        )
        if installed_path != public_path or file_sha256(installed_file) != selected["sha256"]:
            raise RuntimeError(f"installed cover verification failed: {book.path}")
        result["status"] = "saved"
        result["updated_at"] = now()
    return result


def parse_ids(values):
    result = set()
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item and not item.isdigit():
                raise ValueError(f"invalid Goodreads ID {item!r}")
            if item:
                result.add(item)
    return result


def run(limit, ids, dry_run, resume, api_key, delay):
    if limit is not None and limit < 0:
        raise ValueError("--limit must be zero or greater")
    if delay < 0:
        raise ValueError("--delay must be zero or greater")
    books = load_existing_books()
    protected = snapshot_protected(books)
    originals = {book.path: book.path.read_bytes() for book in books}
    eligible = [
        book
        for book in books
        if str(book.data.get("goodreads_id") or "").strip()
    ]
    by_id = {str(book.data["goodreads_id"]).strip(): book for book in eligible}
    if len(by_id) != len(eligible):
        raise ValueError("duplicate goodreads_id in collection")
    unknown = ids - set(by_id)
    if unknown:
        raise ValueError(f"unknown Goodreads IDs: {', '.join(sorted(unknown, key=int))}")
    if ids:
        eligible = [book for book in eligible if str(book.data["goodreads_id"]) in ids]
    report, pending, resumed = load_report(), [], 0
    for book in eligible:
        goodreads_id = str(book.data["goodreads_id"]).strip()
        if resume and goodreads_id in report and resume_current(
            book, report[goodreads_id], dry_run
        ):
            resumed += 1
        else:
            pending.append(book)
    if limit is not None:
        pending = pending[:limit]
    session, counts = build_session(), {}
    try:
        for index, book in enumerate(pending, 1):
            goodreads_id = str(book.data["goodreads_id"]).strip()
            try:
                result = process_book(
                    session, book, originals[book.path], api_key, dry_run
                )
            except Exception as error:
                result = result_base(book)
                result.update(
                    status="error",
                    reasons=[f"{error.__class__.__name__}:{error}"],
                    candidates=[],
                )
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1
            print(f"[{index}/{len(pending)}] Goodreads {goodreads_id}: {status}")
            if not dry_run:
                report[goodreads_id] = result
                write_report(report)
            assert_protected_unchanged(protected)
            if delay and index < len(pending):
                time.sleep(delay)
    finally:
        session.close()
    assert_protected_unchanged(protected)
    summary = ", ".join(f"{key}={counts[key]}" for key in sorted(counts)) or "none"
    print(
        f"{'Dry run' if dry_run else 'Cover enrichment'} complete: "
        f"attempted={len(pending)}, resumed={resumed}, "
        f"protected={len(protected[0])}; {summary}."
    )
    if not api_key:
        print("Google Books skipped (pass --google-api-key to opt in).")


def make_test_image(width, height):
    image = Image.new("RGB", (width, height), "#173A5E")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, width - 20, height - 20), outline="#E0AA52", width=8)
    draw.polygon(
        (
            (width // 5, height // 6),
            (width * 4 // 5, height // 3),
            (width // 2, height * 5 // 6),
        ),
        fill="#D98732",
    )
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def self_check():
    assert canonical_isbn("0-306-40615-2") == "9780306406157"
    assert not canonical_isbn("9780306406158")
    assert goodreads_url_has_id(
        "https://www.goodreads.com/book/show/42-example", "42"
    )
    parser = GoodreadsMetaParser()
    parser.feed(
        '<link rel="canonical" href="https://www.goodreads.com/book/show/42-book">'
        '<meta property="og:image" content="https://images.example/cover.jpg">'
    )
    assert parser.identity_urls and parser.image_urls
    good, normalized = inspect_image(
        make_test_image(360, 540),
        "image/png",
        "https://images.example/cover.png",
    )
    assert good["status"] == "valid", good
    assert normalized and normalized.startswith(b"\xff\xd8")
    assert good["preferred_dimensions"] is True
    assert extract_dominant_color(normalized)
    small, _ = inspect_image(
        make_test_image(199, 400),
        "image/png",
        "https://images.example/small.png",
    )
    assert "width_below_200" in small["reasons"]
    blank = io.BytesIO()
    Image.new("RGB", (360, 540), "white").save(blank, format="PNG")
    rejected, _ = inspect_image(
        blank.getvalue(),
        "image/png",
        "https://images.example/blank.png",
    )
    assert "blank_or_nearly_blank" in rejected["reasons"]
    bad_mime, _ = inspect_image(
        make_test_image(360, 540),
        "text/html",
        "https://images.example/cover.png",
    )
    assert "non_image_mime:text/html" in bad_mime["reasons"]
    bad_decode, _ = inspect_image(
        b"not an image",
        "image/jpeg",
        "https://images.example/cover.jpg",
    )
    assert "decode_error" in bad_decode["reasons"]
    placeholder, _ = inspect_image(
        make_test_image(360, 540),
        "image/png",
        "https://images.example/nophoto/book.png",
    )
    assert "placeholder_url" in placeholder["reasons"]
    smaller = copy.deepcopy(good)
    smaller["pixel_area"] = 1
    assert select_best([(smaller, b"small"), (good, normalized)])[1] == normalized
    transient = {"status": "no_valid_candidate", "reasons": ["goodreads:http_202"]}
    assert resume_current(None, transient, False) is False
    final = {"status": "no_valid_candidate", "reasons": ["open_library:http_404"]}
    assert resume_current(None, final, False) is True
    print("enrich_book_covers self-check passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--google-api-key",
        help="Explicitly enable exact-ISBN Google Books candidates",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Polite delay between books in seconds (default: 1.0)",
    )
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    run(
        limit=args.limit,
        ids=parse_ids(args.ids),
        dry_run=args.dry_run,
        resume=args.resume,
        api_key=args.google_api_key,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
