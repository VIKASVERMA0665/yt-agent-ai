"""Stock image downloader for YT Agent AI — Pixabay API."""
import os
import re
import requests
from PIL import Image, ImageDraw, ImageFont
import config

PIXABAY_SEARCH = "https://pixabay.com/api/"

_GENERIC_BY_TYPE = {
    "hook": ["Hindu temple sunrise devotional India", "Indian temple diya aarti", "devotee praying temple India"],
    "cta": ["Hindu temple evening diya India", "Indian temple aarti devotees", "devotional diya flowers temple"],
    "conclusion": ["Hindu temple sunrise peaceful India", "devotee prayer temple India", "diya aarti devotional India"],
    "default": ["Hindu temple devotional India", "Indian temple diya aarti", "Hindu devotee praying India"],
}

def _simplify_query(query: str) -> str:
    q = re.sub(
        r"\b(dramatic|cinematic|wide|shot|close[- ]?up|establishing|specific|abstract|"
        r"symbolic|visual|concept|matching|representing|hope|breakthrough|peaceful|"
        r"beautiful|stunning|revealing|detail|human reaction|reaction shot)\b",
        " ", query, flags=re.I
    )
    q = re.sub(r"[^\w\s-]", " ", q, flags=re.UNICODE)
    return re.sub(r"\s+", " ", q).strip()

def _search_pixabay(api_key: str, query: str, orientation: str, per_page: int = 20) -> list:
    params = {
        "key": api_key, "q": query, "image_type": "photo",
        "orientation": orientation, "per_page": min(max(per_page, 10), 30),
        "safesearch": "true",
    }
    r = requests.get(PIXABAY_SEARCH, params=params, timeout=20)
    if r.status_code == 429:
        print("   ⚠ Pixabay rate limit (429) — skipping this query")
        return []
    r.raise_for_status()
    hits = r.json().get("hits", [])
    hits.sort(key=lambda x: (x.get("downloads", 0), x.get("likes", 0), x.get("views", 0)), reverse=True)
    return hits

def _download_hit(item: dict, path: str) -> bool:
    img_url = item.get("largeImageURL") or item.get("webformatURL")
    if not img_url:
        return False
    try:
        img_r = requests.get(img_url, timeout=30, stream=True)
        img_r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in img_r.iter_content(8192):
                f.write(chunk)
        return os.path.getsize(path) > 1024
    except Exception as e:
        print(f"   ⚠ Pixabay image download failed: {e}")
        return False

def _make_fallback_image(path: str) -> str:
    """Create a visible devotional fallback so an API/search failure never creates a blank video."""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), (18, 10, 30))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        p = y / h
        draw.line((0, y, w, y), fill=(int(18 + 70*p), int(10 + 35*p), int(30 + 8*(1-p))))

    cx, cy = w // 2, int(h * 0.62)

    # Glowing concentric devotional light.
    for radius in range(360, 20, -18):
        a = 1 - radius / 360
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                     outline=(int(120 + 100*a), int(45 + 90*a), 8), width=4)

    # Diya.
    draw.ellipse((cx-215, cy, cx+215, cy+130), fill=(150, 65, 12))
    draw.arc((cx-215, cy-25, cx+215, cy+130), 0, 180, fill=(251, 191, 36), width=8)
    draw.polygon([(cx, cy-260), (cx-72, cy-145), (cx-38, cy-65),
                  (cx, cy-95), (cx+42, cy-55), (cx+78, cy-145)], fill=(251, 191, 36))
    draw.polygon([(cx, cy-205), (cx-32, cy-125), (cx, cy-88), (cx+32, cy-125)],
                 fill=(255, 245, 190))

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 58)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
        small = font

    title = "Bhakti Dhun"
    bbox = draw.textbbox((0, 0), title, font=font)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 90), title, font=font, fill=(255, 240, 190))
    subtitle = "॥ जय श्री राम • हर हर महादेव • राधे राधे ॥"
    bbox = draw.textbbox((0, 0), subtitle, font=small)
    draw.text(((w-(bbox[2]-bbox[0]))//2, 165), subtitle, font=small, fill=(245, 158, 11))

    img.save(path, quality=92)
    return path

def _fetch_images(query: str, section_index: int, images_dir: str,
                  count: int = 1, orientation: str = "landscape",
                  img_num_start: int = 0, fallback_queries=None) -> list:
    """Try the exact Pixabay query, a simplified query, then devotional fallback searches."""
    api_key = getattr(config, "PIXABAY_API_KEY", "")
    if not api_key or api_key.startswith("YOUR_"):
        print("   ⚠ Pixabay API key missing — no stock image for this query")
        return []

    candidates = []
    for q in [query, _simplify_query(query)] + (fallback_queries or []):
        q = q.strip()
        if q and q not in candidates:
            candidates.append(q)

    hits = []
    used_query = ""
    try:
        for q in candidates:
            hits = _search_pixabay(api_key, q, orientation, per_page=max(10, count * 6))
            if hits:
                used_query = q
                break
    except requests.HTTPError as e:
        print(f"   ⚠ Pixabay API error: {e}")
    except Exception as e:
        print(f"   ⚠ Pixabay search failed: {e}")

    if not hits:
        print(f"   ⚠ No Pixabay result for '{query}'")
        return []

    saved = []
    for img_num, item in enumerate(hits[:count]):
        fname = f"section_{section_index:02d}_img{img_num_start + img_num + 1:02d}.jpg"
        path = os.path.join(images_dir, fname)
        if _download_hit(item, path):
            saved.append(path)

    if saved:
        print(f"         ✓ Pixabay: {used_query} → {len(saved)} image(s)")
    return saved

def download_images(script: dict, output_dir: str) -> dict:
    """
    Normal videos get up to three images per section.
    If Pixabay has no usable result, a devotional fallback image is created.
    """
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    is_shorts = script.get("video_type") == "shorts"
    orientation = "portrait" if is_shorts else "landscape"
    image_map = {}

    for section in script.get("sections", []):
        sid = section["id"]
        stype = section.get("section_type", "default")
        queries = [section.get("image_query", "").strip()]
        for extra_key in ("image_query_2", "image_query_3", "image_query_4"):
            q = section.get(extra_key, "").strip()
            if q:
                queries.append(q)
        queries = [q for q in queries if q]

        fallbacks = _GENERIC_BY_TYPE.get(stype, _GENERIC_BY_TYPE["default"])
        wanted = len(queries) if is_shorts else min(3, max(1, len(queries)))

        print(f"   → [{sid}] Pixabay: {len(queries)} queries × 1 image each")
        paths = []
        for qi, q in enumerate(queries[:wanted]):
            paths.extend(_fetch_images(
                q, sid, images_dir, count=1, orientation=orientation,
                img_num_start=qi, fallback_queries=fallbacks
            ))

        if not paths:
            fallback_path = os.path.join(images_dir, f"section_{sid:02d}_fallback.png")
            _make_fallback_image(fallback_path)
            paths = [fallback_path]
            print("         ✓ devotional fallback image created")

        image_map[sid] = paths
        print(f"         saved {len(paths)} image(s)")

    return image_map
