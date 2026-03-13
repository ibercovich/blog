#!/usr/bin/env python3
"""Import books from a CSV into _pages/books.md with cover colors.

Usage:
    python scripts/import_books.py path/to/books.csv
    python scripts/import_books.py path/to/books.csv --google-api-key YOUR_KEY

Reads GOOGLE_BOOKS_API_KEY from scripts/.env if --google-api-key is not given.
CSV format: title, author, isbn (no header row).
"""

import argparse
import csv
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

BLOG_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BLOG_ROOT / "_pages" / "books.md"
COVERS_DIR = BLOG_ROOT / "assets" / "covers"
SYNOPSIS_CACHE = Path(__file__).resolve().parent / "synopsis_cache.json"


def slugify(text):
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:80]


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


def load_existing_books():
    """Parse existing books.md and return a dict keyed by (title, author)."""
    if not OUTPUT_PATH.exists():
        return {}
    text = OUTPUT_PATH.read_text(encoding="utf-8")
    # Extract JSON array from: window.__BOOKS = [...];
    match = re.search(r"window\.__BOOKS\s*=\s*(\[.*?\])\s*;", text, re.DOTALL)
    if not match:
        return {}
    try:
        books = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    # Key by lowercase (title, author) for matching
    return {(b["title"].lower(), b["author"].lower()): b for b in books}


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
    """Re-extract dominant colors for all existing books using okmain."""
    existing = load_existing_books()
    if not existing:
        print("No existing books found in books.md")
        return

    all_books = list(existing.values())
    print(f"Recomputing colors for {len(all_books)} books")

    for i, book in enumerate(all_books):
        title = book["title"]
        cover_path = book.get("cover", "")
        print(f"[{i+1}/{len(all_books)}] {title}")

        if not cover_path:
            print(f"  no cover, keeping color {book.get('color', '')}")
            continue

        # Read cover from local file
        local_file = BLOG_ROOT / cover_path.lstrip("/")
        if not local_file.exists():
            print(f"  cover file missing: {local_file}")
            continue

        image_data = local_file.read_bytes()
        color = extract_dominant_color(image_data)
        if color:
            old = book.get("color", "")
            book["color"] = color
            print(f"  {old} -> {color}")
        else:
            print(f"  extraction failed, keeping {book.get('color', '')}")

    # Sort and write
    all_books.sort(key=lambda b: b["title"].lower())
    books_json = json.dumps(all_books, indent=2, ensure_ascii=False)
    with open(OUTPUT_PATH, "w") as f:
        f.write("---\nlayout: books\ntitle: Books\npermalink: /books/\n---\n\n")
        f.write("<script>\nwindow.__BOOKS = ")
        f.write(books_json)
        f.write(";\n</script>\n")

    print(f"\nWrote {len(all_books)} books to {OUTPUT_PATH}")


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
            isbn = row[2].strip() if len(row) > 2 else ""
            if not isbn:
                normalized = title.replace("\u2019", "'")
                isbn = FALLBACK_ISBNS.get(title, "") or FALLBACK_ISBNS.get(normalized, "")
            books.append({"title": title, "author": author, "isbn": isbn})

    print(f"Loaded {len(books)} books from CSV")
    if api_key:
        print("Using Google Books API key")
    if anthropic_key:
        print("Using Anthropic API key for synopsis cleaning")

    # Load existing books.md data to preserve already-curated fields
    existing_books = load_existing_books()
    if existing_books:
        print(f"Found {len(existing_books)} existing books in books.md")

    synopsis_cache = load_synopsis_cache()

    default_color = "#6b4c3b"
    results = []
    for i, book in enumerate(books):
        display_title = short_title(clean_title(book["title"]))
        full_title = clean_title(book["title"])
        author = book["author"]
        isbn = book["isbn"]
        slug = slugify(display_title)
        print(f"[{i+1}/{len(books)}] {display_title} — {author}")

        # Check if this book already exists in books.md
        existing = existing_books.get((display_title.lower(), author.lower()))
        if existing:
            # Preserve all curated data from the existing entry
            local_path = existing.get("cover", "")
            color = existing.get("color", default_color)
            synopsis = existing.get("synopsis", "")
            print(f"  preserved from books.md (cover={bool(local_path)}, color={color}, synopsis={len(synopsis)} chars)")
            results.append({
                "title": display_title,
                "author": author,
                "isbn": isbn or existing.get("isbn", ""),
                "cover": local_path,
                "color": color,
                "synopsis": synopsis,
            })
            continue

        # New book — fetch cover, color, synopsis as before
        existing_files = list(COVERS_DIR.glob(f"{slug}.*")) if COVERS_DIR.exists() else []
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

        results.append({
            "title": display_title,
            "author": author,
            "isbn": isbn,
            "cover": local_path,
            "color": color,
            "synopsis": synopsis,
        })
        time.sleep(0.25)

    # Sort alphabetically by title
    results.sort(key=lambda b: b["title"].lower())

    # Write output
    books_json = json.dumps(results, indent=2, ensure_ascii=False)
    with open(OUTPUT_PATH, "w") as f:
        f.write("---\nlayout: books\ntitle: Books\npermalink: /books/\n---\n\n")
        f.write("<script>\nwindow.__BOOKS = ")
        f.write(books_json)
        f.write(";\n</script>\n")

    print(f"\nWrote {len(results)} books to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
