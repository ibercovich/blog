#!/usr/bin/env python3
"""Import books from a CSV into the Git-backed ``_books`` collection.

Usage:
    python scripts/import_books.py path/to/books.csv
    python scripts/import_books.py path/to/books.csv --google-api-key YOUR_KEY

Reads GOOGLE_BOOKS_API_KEY from scripts/.env if --google-api-key is not given.
CSV format: title, author, isbn (no header row).

Imports merge into the existing collection. Books that are not present in the
CSV are left untouched, as are Decap-managed fields on existing books.
"""

import argparse
import csv
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import requests
import yaml
from PIL import Image

BLOG_ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = BLOG_ROOT / "_books"
COVERS_DIR = BLOG_ROOT / "assets" / "covers"
SYNOPSIS_CACHE = Path(__file__).resolve().parent / "synopsis_cache.json"
JEKYLL_DATE_LIKE = re.compile(r"\A\d{1,4}-\d{1,2}-\d{1,2}(?:-|\Z)")


@dataclass
class BookFile:
    """A collection document and its preserved Markdown body."""

    path: Path
    data: dict
    body: str = ""


def slugify(text):
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    slug = re.sub(r"[\s_]+", "-", text).strip("-") or "book"
    if JEKYLL_DATE_LIKE.match(slug):
        slug = f"book-{slug}"
    return slug[:80].rstrip("-")


def fetch_google_cover_url(title, author, isbn, api_key=None):
    """Try Google Books API for a high-res cover URL with exponential backoff."""
    if isbn:
        query = f"isbn:{isbn}"
    else:
        query = f"intitle:{title}+inauthor:{author}"

    params = {"q": query, "maxResults": 1}
    if api_key:
        params["key"] = api_key

    for attempt in range(4):
        try:
            resp = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params=params,
                timeout=10,
            )
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                image_links = items[0].get("volumeInfo", {}).get("imageLinks", {})
                for key in ("extraLarge", "large", "medium", "thumbnail"):
                    if key in image_links:
                        url = image_links[key]
                        url = url.replace("&edge=curl", "").replace("http://", "https://")
                        if "zoom=" in url:
                            url = re.sub(r"zoom=\d+", "zoom=3", url)
                        return url
            return None
        except requests.exceptions.HTTPError:
            return None
        except Exception as e:
            print(f"  Warning: Google Books failed: {e}")
            return None
    print(f"  Google Books: exhausted retries")
    return None


def fetch_openlibrary_cover_url(title, author, isbn):
    """Try Open Library for a cover URL."""
    if isbn:
        return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

    params = {"title": title, "author": author, "limit": 1}
    try:
        resp = requests.get("https://openlibrary.org/search.json", params=params, timeout=10)
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs:
            cover_id = docs[0].get("cover_i")
            if cover_id:
                return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    except Exception as e:
        print(f"  Warning: Open Library failed: {e}")
    return None


def fetch_librarything_cover_url(isbn):
    """Try LibraryThing for a cover URL (ISBN only)."""
    if not isbn:
        return None
    url = f"https://covers.librarything.com/devkey/large/isbn/{isbn}"
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        if resp.status_code == 200 and int(resp.headers.get("content-length", 0)) > 1000:
            return url
    except Exception as e:
        print(f"  Warning: LibraryThing failed: {e}")
    return None


def fetch_cover_url(title, author, isbn, api_key=None, prefer_openlibrary=False):
    """Try multiple sources for cover URL. LibraryThing is always last fallback."""
    if prefer_openlibrary:
        sources = [
            ("LibraryThing", lambda: fetch_librarything_cover_url(isbn)),
            ("Open Library", lambda: fetch_openlibrary_cover_url(title, author, isbn)),
            ("Google Books", lambda: fetch_google_cover_url(title, author, isbn, api_key)),
        ]
    else:
        sources = [
            ("Google Books", lambda: fetch_google_cover_url(title, author, isbn, api_key)),
            ("Open Library", lambda: fetch_openlibrary_cover_url(title, author, isbn)),
            ("LibraryThing", lambda: fetch_librarything_cover_url(isbn)),
        ]
    for name, fn in sources:
        url = fn()
        if url:
            print(f"  source: {name}")
            return url
    return None


def download_cover(url, slug):
    """Download cover image to assets/covers/, return local path and image bytes."""
    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: download failed: {e}")
        return None, None

    data = resp.content
    # Detect format from content
    if data[:4] == b"\x89PNG":
        ext = "png"
    else:
        ext = "jpg"

    filename = f"{slug}.{ext}"
    filepath = COVERS_DIR / filename
    filepath.write_bytes(data)
    return f"/assets/covers/{filename}", data


def extract_dominant_color(image_data):
    """Extract dominant color from image bytes using okmain (Oklab K-means)."""
    from io import BytesIO
    try:
        img = Image.open(BytesIO(image_data)).convert("RGB")
    except Exception:
        return None

    try:
        import okmain
        colors = okmain.colors(img)
        if colors:
            return colors[0].to_hex()
    except ImportError:
        pass

    # Fallback: simple quantization if okmain is not installed
    img = img.resize((50, 50))
    img = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT).convert("RGB")
    pixels = list(img.getdata())

    counts = Counter(pixels)
    for color, _ in counts.most_common():
        r, g, b = color
        if r > 230 and g > 230 and b > 230:
            continue
        if r < 25 and g < 25 and b < 25:
            continue
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def fetch_google_synopsis(title, author, isbn, api_key=None):
    """Get book description from Google Books API."""
    if isbn:
        query = f"isbn:{isbn}"
    else:
        query = f"intitle:{title}+inauthor:{author}"

    params = {"q": query, "maxResults": 1}
    if api_key:
        params["key"] = api_key

    for attempt in range(4):
        try:
            resp = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params=params,
                timeout=10,
            )
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                desc = items[0].get("volumeInfo", {}).get("description", "")
                if desc:
                    return desc
            return None
        except Exception as e:
            print(f"  Warning: Google Books synopsis failed: {e}")
            return None
    return None


def fetch_openlibrary_synopsis(isbn):
    """Get book description from Open Library Works API."""
    if not isbn:
        return None
    try:
        resp = requests.get(
            f"https://openlibrary.org/isbn/{isbn}.json", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        # Follow the works key to get the description
        works = data.get("works", [])
        if works:
            work_key = works[0].get("key", "")
            if work_key:
                resp2 = requests.get(
                    f"https://openlibrary.org{work_key}.json", timeout=10
                )
                resp2.raise_for_status()
                work_data = resp2.json()
                desc = work_data.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")
                if desc:
                    return desc
    except Exception as e:
        print(f"  Warning: Open Library synopsis failed: {e}")
    return None


def clean_synopsis_llm(raw_synopsis, title, author, anthropic_key):
    """Use Claude to condense a raw synopsis to ~2 clean sentences."""
    if not anthropic_key or not raw_synopsis:
        return raw_synopsis
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": (
                    f"Rewrite this book synopsis for \"{title}\" by {author} "
                    f"into roughly two sentences focused purely on what the book is about. "
                    f"Remove any reviews, recommendations, bestseller tags, award mentions, "
                    f"movie/adaptation mentions, \"provided by publisher\", and hype phrases. "
                    f"Just describe the book's content concisely.\n\n{raw_synopsis}"
                )}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()["content"][0]["text"].strip()
        if result:
            return result
    except Exception as e:
        print(f"  Warning: LLM synopsis cleaning failed: {e}")
    return raw_synopsis


def fetch_synopsis(title, author, isbn, api_key=None, anthropic_key=None):
    """Try Google Books then Open Library for a synopsis, clean with LLM."""
    desc = fetch_google_synopsis(title, author, isbn, api_key)
    if desc:
        print(f"  synopsis: Google Books ({len(desc)} chars)")
        desc = clean_synopsis_llm(desc, title, author, anthropic_key)
        print(f"  synopsis cleaned: ({len(desc)} chars)")
        return desc
    desc = fetch_openlibrary_synopsis(isbn)
    if desc:
        print(f"  synopsis: Open Library ({len(desc)} chars)")
        desc = clean_synopsis_llm(desc, title, author, anthropic_key)
        print(f"  synopsis cleaned: ({len(desc)} chars)")
        return desc
    print(f"  synopsis: not found")
    return ""


def load_synopsis_cache():
    """Load cached synopses from disk."""
    if SYNOPSIS_CACHE.exists():
        return json.loads(SYNOPSIS_CACHE.read_text(encoding="utf-8"))
    return {}


def save_synopsis_cache(cache):
    """Save synopses cache to disk."""
    SYNOPSIS_CACHE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)


def read_book_file(path):
    """Read one collection document without discarding its Markdown body."""
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path} does not contain valid YAML front matter")

    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} front matter must be a mapping")
    return BookFile(path=path, data=data, body=text[match.end():])


def write_book_file(book):
    """Write one collection document while retaining all metadata and its body."""
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(
        book.data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    ).rstrip()
    text = f"---\n{front_matter}\n---\n{book.body}"

    if book.path.exists() and book.path.read_text(encoding="utf-8") == text:
        return False

    # A sibling temporary file keeps an interrupted write from truncating a
    # collection document. Path.replace is atomic on the same filesystem.
    temporary_path = book.path.with_name(f".{book.path.name}.tmp")
    try:
        temporary_path.write_text(text, encoding="utf-8")
        temporary_path.replace(book.path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return True


def load_existing_books():
    """Load every Git-backed collection document, without changing any files."""
    if not BOOKS_DIR.exists():
        return []
    return [read_book_file(path) for path in sorted(BOOKS_DIR.glob("*.md"))]


def normalize_isbn(isbn):
    """Normalize an ISBN for matching and storage."""
    return re.sub(r"[\s-]+", "", str(isbn or "")).upper()


def identity_key(title, author):
    """Return the legacy title/author identity used as an ISBN fallback."""
    return (str(title or "").strip().casefold(), str(author or "").strip().casefold())


def add_to_indexes(book, by_isbn, by_identity):
    """Index a book and fail closed if the collection contains ambiguity."""
    title = book.data.get("title", "")
    author = book.data.get("author", "")
    identity = identity_key(title, author)
    if not all(identity):
        raise ValueError(f"{book.path} must define non-empty title and author fields")
    if identity in by_identity and by_identity[identity].path != book.path:
        raise ValueError(
            f"Duplicate title/author in {by_identity[identity].path} and {book.path}"
        )
    by_identity[identity] = book

    isbn = normalize_isbn(book.data.get("isbn"))
    if isbn:
        if isbn in by_isbn and by_isbn[isbn].path != book.path:
            raise ValueError(f"Duplicate ISBN {isbn} in {by_isbn[isbn].path} and {book.path}")
        by_isbn[isbn] = book


def index_existing_books(books):
    """Build unambiguous indexes for merging CSV rows into the collection."""
    by_isbn = {}
    by_identity = {}
    for book in books:
        add_to_indexes(book, by_isbn, by_identity)
    return by_isbn, by_identity


def unused_book_path(title, isbn=""):
    """Choose a new path without overwriting an unrelated collection document."""
    base = slugify(title) or normalize_isbn(isbn).lower() or "book"
    candidate = BOOKS_DIR / f"{base}.md"
    if not candidate.exists():
        return candidate

    suffix = normalize_isbn(isbn).lower()
    if suffix:
        candidate = BOOKS_DIR / f"{base}-{suffix}.md"
        if not candidate.exists():
            return candidate

    counter = 2
    while True:
        candidate = BOOKS_DIR / f"{base}-{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1


FALLBACK_ISBNS = {
    "The Wright Brothers": "9781476728759",
    "Map and Territory": "9781939311238",
    "Art of Money Getting Or, Golden Rules for Making Money": "9781557094940",
    "Bad Blood: Secrets and Lies in a Silicon Valley Startup": "9781524731656",
    "A Short History of Nearly Everything": "9780767908184",
    "Zero to One: Notes on Startups, or How to Build the Future": "9780804139298",
    "The Ride of a Lifetime: Lessons Learned from 15 Years as CEO of the Walt Disney Company": "9780399592096",
    "Pour Your Heart Into It: How Starbucks Built a Company One Cup at a Time": "9780786883561",
    "Principles: Life and Work": "9781501124020",
    "The Subtle Art of Not Giving a F*ck: A Counterintuitive Approach to Living a Good Life": "9780062457714",
    "The Solar War": "9781940026251",
    "The Solar War (The Long Winter, #2)": "9781940026251",
    "Deep Learning with Keras": "9781617296864",
    "The Three-Body Problem": "9780765382030",
    "The Three-Body Problem (Remembrance of Earth's Past, #1)": "9780765382030",
    "The Dark Forest": "9780765386694",
    "The Dark Forest (Remembrance of Earth's Past, #2)": "9780765386694",
    "Wool Omnibus": "9781476733951",
    "Wool Omnibus (Silo, #1)": "9781476733951",
}


def clean_author(author):
    """Remove trailing * from author names."""
    return author.rstrip(" *")


def clean_title(title):
    """Remove series info in parentheses from titles."""
    return re.sub(r"\s*\([^)]*#\d+\)\s*$", "", title)


def short_title(title):
    """Return a short display title (strip subtitle after colon)."""
    if ":" in title:
        return title.split(":")[0].strip()
    return title


def recompute_colors():
    """Re-extract colors in place without rebuilding collection documents."""
    books = load_existing_books()
    if not books:
        print(f"No existing books found in {BOOKS_DIR}")
        return

    print(f"Recomputing colors for {len(books)} books")
    updated = 0

    for i, book in enumerate(books):
        title = book.data.get("title", book.path.stem)
        cover_path = str(book.data.get("cover", "") or "")
        print(f"[{i+1}/{len(books)}] {title}")

        if not cover_path:
            print(f"  no cover, keeping color {book.data.get('color', '')}")
            continue

        # Covers should be repository-local. Refuse paths that escape the blog
        # root rather than reading arbitrary files named in front matter.
        local_file = (BLOG_ROOT / cover_path.lstrip("/")).resolve()
        try:
            local_file.relative_to(BLOG_ROOT.resolve())
        except ValueError:
            print(f"  unsafe cover path, keeping color {book.data.get('color', '')}")
            continue
        if not local_file.exists():
            print(f"  cover file missing: {local_file}")
            continue

        try:
            color = extract_dominant_color(local_file.read_bytes())
        except Exception as error:
            print(f"  extraction failed ({error}), keeping {book.data.get('color', '')}")
            continue
        if color:
            old = book.data.get("color", "")
            if color == old:
                print(f"  unchanged: {color}")
                continue
            book.data["color"] = color
            write_book_file(book)
            updated += 1
            print(f"  {old} -> {color}")
        else:
            print(f"  extraction failed, keeping {book.data.get('color', '')}")

    print(f"\nUpdated {updated} of {len(books)} collection documents")


def main():
    parser = argparse.ArgumentParser(description="Import books from CSV")
    parser.add_argument("csvfile", nargs="?", help="Path to the books CSV")
    parser.add_argument("--recompute-colors", action="store_true",
                        help="Re-extract colors from existing covers (no CSV needed)")
    parser.add_argument("--google-api-key", help="Google Books API key for higher-res covers")
    parser.add_argument("--prefer-openlibrary", action="store_true",
                        help="Try Open Library before Google Books (for re-fetching bad covers)")
    args = parser.parse_args()

    if args.recompute_colors:
        recompute_colors()
        return

    if not args.csvfile:
        parser.error("csvfile is required unless --recompute-colors is used")

    # Load API keys: CLI arg > .env file > none
    api_key = args.google_api_key
    anthropic_key = None
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not api_key and line.startswith("GOOGLE_BOOKS_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                anthropic_key = line.split("=", 1)[1].strip()

    books = []
    with open(args.csvfile, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            title = row[0].strip()
            author = clean_author(row[1].strip())
            if not title or not author:
                print(f"Skipping row with missing title or author: {row!r}")
                continue
            isbn = normalize_isbn(row[2]) if len(row) > 2 else ""
            if not isbn:
                normalized = title.replace("\u2019", "'")
                isbn = normalize_isbn(
                    FALLBACK_ISBNS.get(title, "")
                    or FALLBACK_ISBNS.get(normalized, "")
                )
            books.append({"title": title, "author": author, "isbn": isbn})

    print(f"Loaded {len(books)} books from CSV")
    if api_key:
        print("Using Google Books API key")
    if anthropic_key:
        print("Using Anthropic API key for synopsis cleaning")

    # Load the complete collection before writing anything. This both protects
    # arbitrary Decap fields and catches ambiguous records before an import.
    existing_books = load_existing_books()
    by_isbn, by_identity = index_existing_books(existing_books)
    if existing_books:
        print(f"Found {len(existing_books)} existing books in {BOOKS_DIR}")

    synopsis_cache = load_synopsis_cache()

    default_color = "#6b4c3b"
    created = 0
    updated = 0
    preserved = 0
    for i, book in enumerate(books):
        display_title = short_title(clean_title(book["title"]))
        full_title = clean_title(book["title"])
        author = book["author"]
        isbn = normalize_isbn(book["isbn"])
        slug = slugify(display_title)
        print(f"[{i+1}/{len(books)}] {display_title} — {author}")

        # ISBN is the stable identity when available. Title and author retain
        # compatibility with older CSV files that omit it.
        existing = by_isbn.get(isbn) if isbn else None
        if existing is None:
            existing = by_identity.get(identity_key(display_title, author))
        if existing:
            # Keep the existing document—including status, collections,
            # recommendations, dates, unknown future fields, and body. Only
            # fill a missing ISBN when the CSV supplies one.
            existing_isbn = normalize_isbn(existing.data.get("isbn"))
            if isbn and not existing_isbn:
                existing.data["isbn"] = isbn
                by_isbn[isbn] = existing
                if write_book_file(existing):
                    updated += 1
                print("  added missing ISBN; preserved all other collection metadata")
            else:
                if isbn and existing_isbn and isbn != existing_isbn:
                    print(
                        f"  ISBN differs ({isbn} vs {existing_isbn}); "
                        "preserving the collection value"
                    )
                preserved += 1
                print("  already in collection; preserved without changes")
            continue

        # New book — fetch cover, color, synopsis as before
        existing_files = sorted(COVERS_DIR.glob(f"{slug}.*")) if COVERS_DIR.exists() else []
        if existing_files:
            local_path = f"/assets/covers/{existing_files[0].name}"
            image_data = existing_files[0].read_bytes()
            print(f"  cached: {existing_files[0].name}")
        else:
            cover_url = fetch_cover_url(full_title, author, isbn, api_key,
                                        prefer_openlibrary=args.prefer_openlibrary)
            if cover_url:
                local_path, image_data = download_cover(cover_url, slug)
            else:
                local_path, image_data = None, None

        color = default_color
        if image_data:
            extracted = extract_dominant_color(image_data)
            if extracted:
                color = extracted
                print(f"  color: {color}")
            else:
                print(f"  using default color")
        else:
            print(f"  no cover found, using default color")
            local_path = ""

        # Fetch synopsis (cached)
        cache_key = isbn or slug
        if cache_key in synopsis_cache:
            synopsis = synopsis_cache[cache_key]
            if synopsis:
                print(f"  synopsis: cached ({len(synopsis)} chars)")
            else:
                print(f"  synopsis: cached (none)")
        else:
            synopsis = fetch_synopsis(full_title, author, isbn, api_key, anthropic_key)
            synopsis_cache[cache_key] = synopsis
            save_synopsis_cache(synopsis_cache)

        data = {
            "title": display_title,
            "author": author,
            "isbn": isbn,
            "cover": local_path,
            "color": color,
            "status": "read",
            "collections": [],
            "synopsis": synopsis,
        }
        new_book = BookFile(path=unused_book_path(display_title, isbn), data=data)
        add_to_indexes(new_book, by_isbn, by_identity)
        write_book_file(new_book)
        created += 1
        print(f"  wrote {new_book.path.relative_to(BLOG_ROOT)}")
        time.sleep(0.25)

    print(
        f"\nImport complete: {created} added, {updated} updated, "
        f"{preserved} already present. {len(by_identity)} books in collection."
    )


if __name__ == "__main__":
    main()
