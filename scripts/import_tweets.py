#!/usr/bin/env python3
"""Import tweets from a Twitter archive zip into _pages/tweets.md.

Usage:
    python scripts/import_tweets.py path/to/twitter-archive.zip
    python scripts/import_tweets.py path/to/twitter-archive.zip --exclude tweets-kept.json

When --exclude is given, any tweet IDs present in the current tweets.md
but absent from the kept JSON are added to the blocklist.
"""

import argparse
import html as html_mod
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BLOG_ROOT / "_pages" / "tweets.md"
MEDIA_DIR = BLOG_ROOT / "assets" / "tweets"
USERNAME = "neversupervised"


def parse_existing(path: Path) -> tuple[dict[str, dict], list[str]]:
    """Parse existing tweets.md. Returns (tweets_by_id, blocked_ids)."""
    if not path.exists():
        return {}, []

    content = path.read_text()

    tweets = {}
    m = re.search(r"window\.__TWEETS\s*=\s*(\[.*?\]);\s*\n", content, re.DOTALL)
    if m:
        tweets = {t["id"]: t for t in json.loads(m.group(1))}

    blocked = []
    m = re.search(r"window\.__BLOCKED\s*=\s*(\[.*?\]);\s*\n", content, re.DOTALL)
    if m:
        blocked = json.loads(m.group(1))

    return tweets, blocked


def load_js_array(zf: zipfile.ZipFile, name: str) -> list:
    """Read a window.YTD.*.part0 JS file from the archive as JSON."""
    try:
        raw = zf.read(name).decode("utf-8")
    except KeyError:
        return []
    eq = raw.index("=")
    return json.loads(raw[eq + 1 :])


def build_article_links(
    tweets: list[dict],
    articles: list[dict],
    article_metadata: list[dict],
) -> dict[str, dict[str, str]]:
    """Map article-post tweet IDs to title-only links on X."""
    article_tweet_ids = {
        item.get("articleMetadata", {}).get("tweetId")
        for item in article_metadata
    }
    article_tweet_ids.discard(None)

    titles_by_id = {}
    for item in articles:
        article = item.get("article", {})
        article_id = str(article.get("id", ""))
        title = article.get("title", "")
        if article_id and title:
            titles_by_id[article_id] = title

    links = {}
    for item in tweets:
        tw = item["tweet"]
        if tw["id_str"] not in article_tweet_ids:
            continue
        for url in tw.get("entities", {}).get("urls", []):
            expanded = url.get("expanded_url") or url.get("expandedUrl") or ""
            match = re.fullmatch(
                r"https?://(?:www\.)?x\.com/i/article/(\d+)/?", expanded
            )
            if not match:
                continue

            article_id = match.group(1)
            title = titles_by_id.get(article_id)
            if title:
                links[tw["id_str"]] = {
                    "title": title,
                    "url": f"https://x.com/i/article/{article_id}",
                }
            break

    return links


def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%a %b %d %H:%M:%S %z %Y")


def parse_iso_date(d: str) -> datetime:
    return datetime.fromisoformat(d.replace("Z", "+00:00"))


def expand_urls(text: str, urls: list[dict]) -> str:
    """Expand URL entities from either tweet or note-tweet records."""
    for url in urls:
        short = url.get("url") or url.get("shortUrl") or ""
        expanded = (
            url.get("expanded_url")
            or url.get("expandedUrl")
            or short
        )
        if short and expanded:
            text = text.replace(short, expanded)
    return text


def expand_note_text(
    ft: str,
    created: datetime,
    note_by_created: dict[datetime, str],
    note_by_prefix: dict[str, str],
) -> str:
    """Replace a truncated tweet body with its full note-tweet text."""
    suffix_match = re.search(r"(?P<suffix>(?:\s+https://t\.co/\S+)+\s*)$", ft)
    suffix = suffix_match.group("suffix") if suffix_match else ""
    body = ft[: suffix_match.start()] if suffix_match else ft
    body = body.rstrip()

    if not body.endswith("\u2026"):
        return ft

    note_text = note_by_created.get(created)
    if note_text is None:
        # Fall back to text matching for archives whose timestamps do not align.
        truncated = body.rstrip("\u2026").strip()
        candidates = [truncated]
        without_reply_mentions = re.sub(
            r"^(?:@[A-Za-z0-9_]{1,15}\s+)+", "", truncated
        )
        if without_reply_mentions != truncated:
            candidates.append(without_reply_mentions)
        for candidate in candidates:
            note_text = note_by_prefix.get(candidate[:30])
            if note_text is not None:
                break

    if note_text is None:
        return ft

    # Twitter omits automatic reply recipients from note-tweet text, so retain
    # any leading handles from the regular tweet record.
    leading_match = re.match(r"^(?:@[A-Za-z0-9_]{1,15}\s+)+", body)
    leading_handles = (
        re.findall(r"@[A-Za-z0-9_]{1,15}", leading_match.group(0))
        if leading_match
        else []
    )
    note_handles = []
    note_remainder = note_text.lstrip()
    while note_handle_match := re.match(
        r"@[A-Za-z0-9_]{1,15}\b", note_remainder
    ):
        note_handles.append(note_handle_match.group(0))
        note_remainder = note_remainder[note_handle_match.end() :].lstrip()

    overlap = 0
    for size in range(min(len(leading_handles), len(note_handles)), 0, -1):
        if [h.casefold() for h in leading_handles[-size:]] == [
            h.casefold() for h in note_handles[:size]
        ]:
            overlap = size
            break
    retained_handles = leading_handles[: len(leading_handles) - overlap]
    leading = f"{' '.join(retained_handles)} " if retained_handles else ""

    return f"{leading}{note_text}{suffix}"


def extract_media(zf: zipfile.ZipFile, tid: str, tw: dict) -> list[str]:
    """Extract media files for a tweet, return list of relative asset paths."""
    media = (
        tw.get("extended_entities", {}).get("media", [])
        or tw.get("entities", {}).get("media", [])
    )
    if not media:
        return []

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for m in media:
        if m.get("type") != "photo":
            continue
        media_url = m.get("media_url", "")
        media_filename = media_url.rsplit("/", 1)[-1] if "/" in media_url else ""
        if not media_filename:
            continue

        prefix = f"data/tweets_media/{tid}-"
        exact = [n for n in zf.namelist() if n.startswith(prefix) and media_filename in n]
        candidates = [n for n in zf.namelist() if n.startswith(prefix) and n.endswith(media_filename.rsplit(".", 1)[-1])]
        archive_path = (exact or candidates or [None])[0]
        if not archive_path:
            continue

        out_name = f"{tid}-{media_filename}"
        out_path = MEDIA_DIR / out_name
        if not out_path.exists():
            out_path.write_bytes(zf.read(archive_path))
        paths.append(f"/assets/tweets/{out_name}")
    return paths


def restore_missing_media(
    zf: zipfile.ZipFile, tweets: dict[str, dict]
) -> int:
    """Restore referenced tweet images that are present in the archive."""
    archive_names = set(zf.namelist())
    restored = 0

    for entry in tweets.values():
        for image_path in entry.get("images", []):
            filename = Path(image_path).name
            output_path = MEDIA_DIR / filename
            if output_path.exists():
                continue

            archive_path = f"data/tweets_media/{filename}"
            if archive_path not in archive_names:
                continue

            MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(zf.read(archive_path))
            restored += 1

    return restored


def process_tweet(
    tw: dict,
    note_by_created: dict[datetime, str],
    note_by_prefix: dict[str, str],
    thread_num: int | None = None,
) -> dict:
    """Convert a raw tweet dict into a clean data object with HTML formatting."""
    tid = tw["id_str"]
    ft = tw["full_text"]
    created = parse_date(tw["created_at"])

    # Expand with note-tweet full text
    ft = expand_note_text(ft, created, note_by_created, note_by_prefix)

    urls = tw.get("entities", {}).get("urls", [])

    # Expand t.co URLs in the plain text first
    ft = expand_urls(ft, urls)

    # Remove trailing t.co media URLs
    ft = re.sub(r"\s*https://t\.co/\S+\s*$", "", ft)

    # Add thread numbering if part of an unlabeled self-reply chain
    if thread_num is not None and not re.match(r"^\d+/", ft):
        ft = f"{thread_num}/ {ft}"

    # Escape HTML, then apply links and mentions
    ft = html_mod.escape(ft)

    # Linkify URLs and visible @mentions in one pass so archive metadata
    # omissions cannot leave reply handles unlinked.
    def linkify(match: re.Match) -> str:
        value = match.group(0)
        if value.startswith(("http://", "https://")):
            trailing = ""
            while value:
                char = value[-1]
                is_punctuation = char in ".,:!?"
                is_semicolon = char == ";" and not value.endswith("&amp;")
                is_unmatched_closer = (
                    char in ")]}"
                    and value.count(char)
                    > value.count({")": "(", "]": "[", "}": "{"}[char])
                )
                if not (is_punctuation or is_semicolon or is_unmatched_closer):
                    break
                trailing = char + trailing
                value = value[:-1]
            return (
                f'<a href="{value}" target="_blank" rel="noopener">{value}</a>'
                f"{trailing}"
            )
        screen_name = value[1:]
        return (
            f'<a href="https://x.com/{screen_name}" target="_blank" '
            f'rel="noopener">{value}</a>'
        )

    ft = re.sub(
        r"https?://(?:[^\s<>&]|&amp;)+|(?<![\w@])@[A-Za-z0-9_]{1,15}\b",
        linkify,
        ft,
    )

    return {
        "id": tid,
        "date": created.strftime("%Y-%m-%d"),
        "html": ft,
    }


def build_thread_chains(tweets: list[dict], kept_ids: set[str]) -> dict[str, int]:
    """Build thread numbering for self-reply chains.

    Returns {tweet_id: thread_position} (1-indexed) for tweets in chains
    of 2+ among the kept set. Skips tweets already labeled with N/ prefix.
    """
    # Build reply map from archive
    reply_map: dict[str, str] = {}
    tweet_text: dict[str, str] = {}
    for t in tweets:
        tw = t["tweet"]
        tid = tw["id_str"]
        reply_to = tw.get("in_reply_to_status_id_str")
        if reply_to:
            reply_map[tid] = reply_to
        tweet_text[tid] = tw["full_text"]

    # Build parent -> children map among kept tweets
    children: dict[str, list[str]] = {}
    for tid, parent in reply_map.items():
        if tid in kept_ids and parent in kept_ids:
            children.setdefault(parent, []).append(tid)

    # Find thread roots: kept tweets with children whose parent isn't a kept reply
    roots = set()
    for parent in children:
        if parent not in reply_map or reply_map[parent] not in kept_ids:
            roots.add(parent)

    # Walk each chain and assign positions
    numbering: dict[str, int] = {}
    for root in roots:
        chain = [root]
        current = root
        while current in children:
            kids = sorted(children[current], key=int)
            current = kids[0]
            chain.append(current)

        if len(chain) < 2:
            continue

        # Skip chains where the root is already manually labeled
        root_text = tweet_text.get(root, "")
        if re.match(r"^\d+/", root_text):
            continue

        for i, tid in enumerate(chain, 1):
            numbering[tid] = i

    return numbering


def build_edit_groups(tweets: list[dict]) -> dict[str, str]:
    """Build a mapping from older edit IDs to the newest edit ID.

    Twitter's edit_info.initial.editTweetIds lists all versions of a tweet.
    The last ID in the list is the most recent version.
    Returns {old_id: newest_id} for all non-final versions.
    """
    superseded: dict[str, str] = {}
    for t in tweets:
        tw = t["tweet"]
        edit_ids = tw.get("edit_info", {}).get("initial", {}).get("editTweetIds", [])
        if len(edit_ids) > 1:
            # Sort by ID (numeric) — highest is newest
            sorted_ids = sorted(edit_ids, key=int)
            newest = sorted_ids[-1]
            for old_id in sorted_ids[:-1]:
                superseded[old_id] = newest
    return superseded


def write_output(tweets: list[dict], blocked: list[str]):
    """Write tweets.md with inline JSON."""
    tweets_json = json.dumps(tweets, indent=2, ensure_ascii=False)
    blocked_json = json.dumps(sorted(blocked, key=int, reverse=True))

    with open(OUTPUT_PATH, "w") as f:
        f.write("---\nlayout: tweets\ntitle: Tweets\npermalink: /tweets/\n---\n\n")
        f.write("<script>\nwindow.__TWEETS = ")
        f.write(tweets_json)
        f.write(";\nwindow.__BLOCKED = ")
        f.write(blocked_json)
        f.write(";\n</script>\n")


def main():
    parser = argparse.ArgumentParser(description="Import tweets from Twitter archive zip")
    parser.add_argument("zipfile", help="Path to the Twitter archive .zip")
    parser.add_argument("--exclude", help="Path to a tweets-kept.json to derive exclusions from")
    args = parser.parse_args()

    zf = zipfile.ZipFile(args.zipfile)

    tweets = load_js_array(zf, "data/tweets.js")
    notes = load_js_array(zf, "data/note-tweet.js")
    articles = load_js_array(zf, "data/article.js")
    article_metadata = load_js_array(zf, "data/article-metadata.js")
    article_links = build_article_links(
        tweets,
        articles,
        article_metadata,
    )

    # Build note-tweet lookup
    note_by_created: dict[datetime, str] = {}
    note_by_prefix: dict[str, str] = {}
    for n in notes:
        core = n["noteTweet"]["core"]
        text = expand_urls(core["text"], core.get("urls", []))
        note_by_created[parse_iso_date(n["noteTweet"]["createdAt"])] = text
        note_by_prefix[text[:30]] = text

    # Build edit dedup map: old_id -> newest_id
    superseded = build_edit_groups(tweets)
    print(f"Edit groups found: {len(set(superseded.values()))}, superseded versions: {len(superseded)}")

    # Build set of all tweet IDs in archive for self-reply detection
    archive_ids = {t["tweet"]["id_str"] for t in tweets}
    user_id = None
    try:
        acct = load_js_array(zf, "data/account.js")
        user_id = acct[0]["account"]["accountId"]
    except (KeyError, IndexError):
        pass

    # Filter: own tweets + replies, no RTs, no superseded edits
    filtered = []
    for t in tweets:
        tw = t["tweet"]
        tid = tw["id_str"]
        ft = tw["full_text"]
        if ft.startswith("RT @"):
            continue
        if tid in superseded:
            continue
        filtered.append(tw)

    # Load existing data
    existing, blocked = parse_existing(OUTPUT_PATH)
    blocked_set = set(blocked)

    # Handle --exclude: derive new blocklist entries from kept JSON
    if args.exclude:
        with open(args.exclude) as f:
            kept = json.load(f)
        kept_ids = {t["id"] for t in kept}
        # Any tweet currently in the page but not in kept = newly blocked
        for tid in existing:
            if tid not in kept_ids and tid not in blocked_set:
                blocked_set.add(tid)
                print(f"  Blocking: {tid}")
        print(f"New exclusions from kept file: {len(blocked_set) - len(blocked)}")

    # Compute which tweet IDs will be kept (for thread detection)
    kept_ids = {tw["id_str"] for tw in filtered if tw["id_str"] not in blocked_set}
    kept_ids |= {tid for tid in existing if tid not in blocked_set}

    # Build thread numbering for self-reply chains
    thread_nums = build_thread_chains(tweets, kept_ids)
    if thread_nums:
        thread_count = sum(1 for v in thread_nums.values() if v == 1)
        print(f"Threads auto-labeled: {thread_count} ({len(thread_nums)} tweets)")

    print(f"Existing tweets in tweets.md: {len(existing)}")
    print(f"Blocked tweet IDs: {len(blocked_set)}")
    print(f"Filtered tweets in archive: {len(filtered)}")

    # Merge: keep existing, add new from archive, skip blocked
    all_tweets: dict[str, dict] = {}

    # Keep existing tweets that aren't blocked
    for tid, entry in existing.items():
        if tid not in blocked_set:
            all_tweets[tid] = entry

    # Add/update from archive, skip blocked
    new_count = 0
    media_count = 0
    for tw in filtered:
        tid = tw["id_str"]
        if tid in blocked_set:
            continue

        if tid in article_links:
            article = article_links[tid]
            title = html_mod.escape(article["title"])
            url = article["url"]
            entry = {
                "id": tid,
                "date": parse_date(tw["created_at"]).strftime("%Y-%m-%d"),
                "html": (
                    f'<a href="{url}" target="_blank" '
                    f'rel="noopener">{title}</a>'
                ),
            }
        else:
            media_paths = extract_media(zf, tid, tw)
            if media_paths:
                media_count += len(media_paths)
            entry = process_tweet(
                tw,
                note_by_created,
                note_by_prefix,
                thread_nums.get(tid),
            )
            if media_paths:
                entry["images"] = media_paths

        if tid not in all_tweets:
            new_count += 1
        all_tweets[tid] = entry

    print(f"New tweets added: {new_count}")
    print(f"Images extracted: {media_count}")
    print(f"Total tweets: {len(all_tweets)}")

    restored_images = restore_missing_media(zf, all_tweets)
    if restored_images:
        print(f"Missing referenced images restored: {restored_images}")

    # Clean up orphaned images
    referenced = set()
    for entry in all_tweets.values():
        for img in entry.get("images", []):
            referenced.add(img.rsplit("/", 1)[-1])

    if MEDIA_DIR.exists():
        removed_images = 0
        for f in MEDIA_DIR.iterdir():
            if f.name not in referenced:
                f.unlink()
                removed_images += 1
        if removed_images:
            print(f"Removed {removed_images} orphaned images")

    # Sort by date descending, then by ID descending for same date
    sorted_tweets = sorted(
        all_tweets.values(),
        key=lambda t: (t["date"], t["id"]),
        reverse=True,
    )

    write_output(sorted_tweets, sorted(blocked_set))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
