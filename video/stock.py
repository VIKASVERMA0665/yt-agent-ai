"""Stock image downloader for YT Agent AI — Pixabay API."""
import os
import random
import requests
import config

PIXABAY_SEARCH = "https://pixabay.com/api/"

def _fetch_images(query: str, section_index: int, images_dir: str,
                  count: int = 1, orientation: str = "landscape",
                  img_num_start: int = 0, topic_hint: str = "") -> list:
    """Download Pixabay images and return local paths. Never falls back to Wikimedia."""
    api_key = getattr(config, "PIXABAY_API_KEY", "")
    if not api_key or api_key.startswith("YOUR_"):
        print("   ⚠ Pixabay API key missing — no stock image for this query")
        return []

    search_query = query
    if topic_hint and topic_hint.lower() not in query.lower():
        search_query = f"{topic_hint} {query}"

    params = {
        "key": api_key,
        "q": search_query,
        "image_type": "photo",
        "orientation": orientation,
        "per_page": min(max(count * 5, 10), 30),
        "safesearch": "true",
    }

    try:
        r = requests.get(PIXABAY_SEARCH, params=params, timeout=20)
        if r.status_code == 429:
            print("   ⚠ Pixabay rate limit (429) — skipping this query")
            return []
        r.raise_for_status()
        hits = r.json().get("hits", [])

        # If the enriched query has no result, retry once with the original query.
        if not hits and search_query != query:
            params["q"] = query
            r = requests.get(PIXABAY_SEARCH, params=params, timeout=20)
            if r.status_code == 429:
                print("   ⚠ Pixabay rate limit (429) — skipping this query")
                return []
            r.raise_for_status()
            hits = r.json().get("hits", [])

        if not hits:
            return []

        random.shuffle(hits)
        saved = []
        for img_num, item in enumerate(hits[:count]):
            img_url = item.get("largeImageURL") or item.get("webformatURL")
            if not img_url:
                continue
            try:
                img_r = requests.get(img_url, timeout=30, stream=True)
                img_r.raise_for_status()
                fname = f"section_{section_index:02d}_img{img_num_start + img_num + 1:02d}.jpg"
                path = os.path.join(images_dir, fname)
                with open(path, "wb") as f:
                    for chunk in img_r.iter_content(8192):
                        f.write(chunk)
                saved.append(path)
            except Exception as e:
                print(f"   ⚠ Pixabay image download failed: {e}")
        return saved

    except requests.HTTPError as e:
        print(f"   ⚠ Pixabay API error for '{search_query}': {e}")
    except Exception as e:
        print(f"   ⚠ Pixabay search failed for '{search_query}': {e}")
    return []


def download_images(script: dict, output_dir: str) -> dict:
    """
    Downloads stock images for every section.
    Shorts: one image per query.
    Normal videos: up to three images per section for B-roll cycling.
    """
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    is_shorts = script.get("video_type") == "shorts"
    orientation = "portrait" if is_shorts else "landscape"

    raw_title = script.get("title", "")
    topic_hint = " ".join(raw_title.split()[:4]) if raw_title else ""

    image_map = {}
    for section in script.get("sections", []):
        sid = section["id"]
        queries = [section.get("image_query", "Hindu temple devotional")]
        for extra_key in ("image_query_2", "image_query_3", "image_query_4"):
            q = section.get(extra_key, "").strip()
            if q:
                queries.append(q)

        if is_shorts:
            print(f"   → [{sid}] Pixabay: {len(queries)} queries × 1 image each")
            paths = []
            for qi, q in enumerate(queries):
                paths.extend(_fetch_images(
                    q, sid, images_dir, count=1, orientation=orientation,
                    img_num_start=qi, topic_hint=topic_hint
                ))
            image_map[sid] = paths
        else:
            print(f"   → [{sid}] Pixabay: {len(queries[:3])} queries × 1 image each")
            paths = []
            for qi, q in enumerate(queries[:3]):
                paths.extend(_fetch_images(
                    q, sid, images_dir, count=1, orientation=orientation,
                    img_num_start=qi, topic_hint=topic_hint
                ))
            image_map[sid] = paths if paths else None

        print(f"         saved {len(paths)} images")

    return image_map
