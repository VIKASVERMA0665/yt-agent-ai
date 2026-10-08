"""
Stock Image Downloader — Pexels API (free tier)
For normal videos : 1 image per section
For Shorts        : 4 images per section (fast-paced visual slideshow)
Images saved to output/images/section_N_imgM.jpg
"""
import os
import random
import requests
import time
import config

PEXELS_SEARCH = "https://api.pexels.com/v1/search"

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

# Wikimedia asks automated clients to identify themselves with a descriptive User-Agent.
WIKIMEDIA_HEADERS = {
    "User-Agent": "YT-Agent-AI/1.0 (Bhakti Dhun devotional video generator; contact via GitHub repository)",
    "Accept": "application/json",
}
WIKIMEDIA_MIN_INTERVAL = 1.5
_last_wikimedia_request = 0.0


def _wikimedia_get(url: str, **kwargs):
    """Rate-limited Wikimedia request with a short 429 backoff."""
    global _last_wikimedia_request
    wait = WIKIMEDIA_MIN_INTERVAL - (time.monotonic() - _last_wikimedia_request)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):
        r = requests.get(url, **kwargs)
        _last_wikimedia_request = time.monotonic()
        if r.status_code != 429:
            return r
        retry_after = r.headers.get("Retry-After")
        try:
            delay = min(max(float(retry_after), 2.0), 20.0)
        except (TypeError, ValueError):
            delay = 5.0 * (attempt + 1)
        print(f"   ⚠ Wikimedia rate limit (429) — waiting {delay:.1f}s…")
        time.sleep(delay)
    return r


def _fetch_wikimedia_images(query: str, section_index: int, images_dir: str,
                             count: int = 1, orientation: str = "landscape",
                             img_num_start: int = 0) -> list:
    """Free no-key fallback using Wikimedia Commons. Saves attribution metadata."""
    saved = []
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": max(count * 3, 10),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1600 if orientation == "landscape" else 1000,
        "format": "json",
        "formatversion": "2",
    }
    try:
        r = _wikimedia_get(WIKIMEDIA_API, params=params, headers=WIKIMEDIA_HEADERS, timeout=20)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", [])
        random.shuffle(pages)
        credits_path = os.path.join(images_dir, "image_credits.json")
        try:
            with open(credits_path, "r", encoding="utf-8") as f:
                credits = __import__("json").load(f)
        except Exception:
            credits = []

        for page in pages:
            if len(saved) >= count:
                break
            info = (page.get("imageinfo") or [{}])[0]
            img_url = info.get("thumburl") or info.get("url")
            if not img_url:
                continue
            try:
                img_r = _wikimedia_get(img_url, headers=WIKIMEDIA_HEADERS, timeout=30, stream=True)
                img_r.raise_for_status()
                fname = f"section_{section_index:02d}_img{img_num_start + len(saved) + 1:02d}.jpg"
                path = os.path.join(images_dir, fname)
                with open(path, "wb") as f:
                    for chunk in img_r.iter_content(8192):
                        f.write(chunk)
                meta = info.get("extmetadata") or {}
                credits.append({
                    "file": fname,
                    "source": page.get("title", ""),
                    "url": page.get("canonicalurl", ""),
                    "artist": (meta.get("Artist") or {}).get("value", ""),
                    "license": (meta.get("LicenseShortName") or {}).get("value", ""),
                })
                saved.append(path)
            except Exception as e:
                print(f"   ⚠ Wikimedia download failed: {e}")

        try:
            with open(credits_path, "w", encoding="utf-8") as f:
                __import__("json").dump(credits, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    except Exception as e:
        print(f"   ⚠ Wikimedia fallback failed for '{query}': {e}")
    return saved

FALLBACK_QUERIES = [
    "Krishna temple devotional India",
    "Mahadev Shiva temple diya India",
    "Hanuman temple aarti devotional",
    "Hindu temple sunrise peaceful",
    "devotee prayer meditation India",
    "diya aarti flowers temple",
]


def _fetch_images(query: str, section_index: int, images_dir: str,
                  count: int = 1, orientation: str = "landscape",
                  img_num_start: int = 0, topic_hint: str = "") -> list:
    """
    Downloads `count` distinct images for a given query.
    img_num_start offsets the filename index (for multi-query sections).
    topic_hint: prepended to the query to boost topical relevance.
    Returns a list of local file paths.
    """
    # Prepend topic hint to improve relevance (e.g. "black holes dramatic wide")
    if topic_hint and topic_hint.lower() not in query.lower():
        search_query = f"{topic_hint} {query}"
    else:
        search_query = query

    headers  = {"Authorization": config.PEXELS_API_KEY}
    saved    = []
    per_page = min(max(count * 3, 15), 40)
    # Randomise page so repeated runs don't fetch the exact same top photos
    page = random.randint(1, 3)

    for attempt_query in [search_query, query] + FALLBACK_QUERIES:
        params = {
            "query":       attempt_query,
            "per_page":    per_page,
            "page":        page,
            "orientation": orientation,
        }
        try:
            r = requests.get(PEXELS_SEARCH, headers=headers, params=params, timeout=15)
            if r.status_code == 401:
                print("   ⚠ Pexels API key unavailable — using Wikimedia Commons fallback")
                return _fetch_wikimedia_images(search_query, section_index, images_dir, count, orientation, img_num_start)
            r.raise_for_status()
            photos = r.json().get("photos", [])

            # If a random page returned nothing, retry page 1
            if not photos and page > 1:
                params["page"] = 1
                r2 = requests.get(PEXELS_SEARCH, headers=headers, params=params, timeout=15)
                photos = r2.json().get("photos", []) if r2.ok else []

            if not photos:
                continue

            photos.sort(key=lambda p: p["width"] * p["height"], reverse=True)
            # Shuffle within top pool so each run picks different images
            top_pool = photos[:max(count * 2, 6)]
            random.shuffle(top_pool)
            selected = top_pool[:count]

            for img_num, photo in enumerate(selected):
                img_url = photo["src"].get("large2x") or photo["src"]["original"]
                try:
                    img_r = requests.get(img_url, timeout=30, stream=True)
                    img_r.raise_for_status()
                    fname = f"section_{section_index:02d}_img{img_num_start + img_num + 1:02d}.jpg"
                    path  = os.path.join(images_dir, fname)
                    with open(path, "wb") as f:
                        for chunk in img_r.iter_content(8192):
                            f.write(chunk)
                    saved.append(path)
                except Exception as e:
                    print(f"   ⚠ Download failed ({img_url[:60]}…): {e}")

            if saved:
                break

        except Exception as e:
            print(f"   ⚠ Pexels search failed for '{attempt_query}': {e}")
            continue

    return saved


def download_images(script: dict, output_dir: str) -> dict:
    """
    Downloads stock images for every section.
    Shorts: returns list of paths per section_id (for slideshow).
    Normal: returns single path or None per section_id (existing behaviour).
    """
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    is_shorts        = script.get("video_type") == "shorts"
    imgs_per_section = 4 if is_shorts else 1
    orientation      = "portrait" if is_shorts else "landscape"

    # Extract a short topic hint from the script title for query enrichment
    raw_title  = script.get("title", "")
    # Keep first 4 words as a concise topic hint
    topic_hint = " ".join(raw_title.split()[:4]) if raw_title else ""

    image_map = {}
    for section in script.get("sections", []):
        sid   = section["id"]
        # Collect all image queries defined for this section
        queries = [section.get("image_query", "science universe space")]
        for extra_key in ("image_query_2", "image_query_3", "image_query_4"):
            q = section.get(extra_key, "").strip()
            if q:
                queries.append(q)

        # For Shorts fetch one image per query; for normal just use first query
        if is_shorts:
            print(f"   → [{sid}] Pexels: {len(queries)} queries × 1 image each")
            paths = []
            for qi, q in enumerate(queries):
                got = _fetch_images(q, sid, images_dir,
                                    count=1, orientation=orientation,
                                    img_num_start=qi, topic_hint=topic_hint)
                paths.extend(got)
            image_map[sid] = paths
            print(f"         saved {len(paths)} images")
        else:
            # Normal video: fetch 3 images per section (for mid-section B-roll cuts)
            print(f"   → [{sid}] Pexels: {len(queries[:3])} queries × 1 image each")
            paths = []
            for qi, q in enumerate(queries[:3]):
                got = _fetch_images(q, sid, images_dir,
                                    count=1, orientation=orientation,
                                    img_num_start=qi, topic_hint=topic_hint)
                paths.extend(got)
            if not paths:
                # No Pexels key/results: use a free no-key Wikimedia Commons fallback.
                for qi, q in enumerate(queries[:3]):
                    got = _fetch_wikimedia_images(q, sid, images_dir, count=1, orientation=orientation, img_num_start=qi)
                    paths.extend(got)
            image_map[sid] = paths if paths else None
            print(f"         saved {len(paths)} images")

    return image_map
