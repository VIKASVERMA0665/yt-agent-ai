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
        "safesearch": "true", "category": "religion",
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

    img.save(path)
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

def _topic_visual_profile(script: dict) -> tuple[str, list[str]]:
    """Return a strict subject anchor and safe fallbacks for this exact devotional topic."""
    source = " ".join([
        str(script.get("topic", "")), str(script.get("title", "")),
        str(script.get("description", "")),
        " ".join(str(s.get("title", "")) + " " + str(s.get("narration", ""))
                 for s in script.get("sections", []))
    ]).lower()

    profiles = [
        (("shailputri", "shailaputri", "शैलपुत्री", "शैलपुत्री माता"),
         "Maa Shailputri", ["Maa Shailputri goddess idol", "Shailputri Mata Navdurga", "Maa Durga goddess idol"]),
        (("brahmacharini", "ब्रह्मचारिणी"), "Maa Brahmacharini",
         ["Maa Brahmacharini Navdurga", "Brahmacharini Mata idol", "Maa Durga goddess idol"]),
        (("chandraghanta", "चंद्रघंटा"), "Maa Chandraghanta",
         ["Maa Chandraghanta Navdurga", "Chandraghanta Mata idol", "Maa Durga goddess idol"]),
        (("kushmanda", "कूष्मांडा", "कुष्मांडा"), "Maa Kushmanda",
         ["Maa Kushmanda Navdurga", "Kushmanda Mata idol", "Maa Durga goddess idol"]),
        (("skandamata", "स्कंदमाता", "स्कन्दमाता"), "Maa Skandamata",
         ["Maa Skandamata Navdurga", "Skandamata Mata idol", "Maa Durga goddess idol"]),
        (("katyayani", "कात्यायनी"), "Maa Katyayani",
         ["Maa Katyayani Navdurga", "Katyayani Mata idol", "Maa Durga goddess idol"]),
        (("kalaratri", "कालरात्रि", "कालरात्री"), "Maa Kalaratri",
         ["Maa Kalaratri Navdurga", "Kalaratri Mata idol", "Maa Durga goddess idol"]),
        (("mahagauri", "महागौरी"), "Maa Mahagauri",
         ["Maa Mahagauri Navdurga", "Mahagauri Mata idol", "Maa Durga goddess idol"]),
        (("siddhidatri", "सिद्धिदात्री"), "Maa Siddhidatri",
         ["Maa Siddhidatri Navdurga", "Siddhidatri Mata idol", "Maa Durga goddess idol"]),
        (("krishna", "radha", "कृष्ण", "राधा", "वृंदावन", "गीता"),
         "Radha Krishna", ["Radha Krishna devotional", "Lord Krishna flute", "Vrindavan Krishna temple"]),
        (("mahadev", "shiva", "shiv", "महादेव", "शिव"),
         "Lord Shiva", ["Lord Shiva devotional", "Shiva lingam temple", "Kedarnath Shiva temple"]),
        (("hanuman", "हनुमान", "बजरंगबली"),
         "Lord Hanuman", ["Lord Hanuman idol", "Hanuman with gada", "Hanuman temple"]),
        (("saraswati", "सरस्वती"), "Maa Saraswati",
         ["Maa Saraswati goddess idol", "Saraswati veena", "Maa Saraswati puja"]),
        (("lakshmi", "लक्ष्मी"), "Maa Lakshmi",
         ["Maa Lakshmi goddess idol", "Lakshmi lotus", "Maa Lakshmi puja"]),
        (("kali", "काली"), "Maa Kali",
         ["Maa Kali goddess idol", "Kali Mata temple", "Maa Kali puja"]),
        (("durga", "दुर्गा", "navratri", "नवरात्रि", "देवी", "शक्ति"),
         "Maa Durga", ["Maa Durga goddess idol", "Durga Mata lion", "Navratri Durga puja"]),
    ]
    for tokens, anchor, fallbacks in profiles:
        if any(token in source for token in tokens):
            return anchor, fallbacks
    return "Hindu devotional", ["Hindu deity idol devotional", "Hindu temple deity statue", "Hindu puja altar"]


def _clean_visual_query(query: str) -> str:
    """Remove vague cinematic wording so the search focuses on visible subjects."""
    query = _simplify_query(str(query or ""))
    query = re.sub(r"\\b(cosmos|stars|galaxy|shocked person|human reaction|abstract art|light breaking through darkness)\\b", " ", query, flags=re.I)
    return re.sub(r"\\s+", " ", query).strip(" -,")


def download_images(script: dict, output_dir: str) -> dict:
    """
    Download scene-specific devotional visuals with a strict deity anchor.
    AI-provided queries are never used alone: every search is anchored to the
    actual topic, and fallbacks stay with the same deity/festival.
    """
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    is_shorts = script.get("video_type") == "shorts"
    orientation = "portrait" if is_shorts else "landscape"
    anchor, safe_fallbacks = _topic_visual_profile(script)
    image_map = {}
    print(f"   🔎 Strict visual subject: {anchor} (Pixabay)")

    for section in script.get("sections", []):
        sid = int(section.get("id", len(image_map) + 1))
        section_text = " ".join([
            str(section.get("title", "")), str(section.get("narration", "")),
            str(section.get("caption_text", ""))
        ]).lower()

        # Prefer AI's scene-specific searches, but prepend the exact deity anchor.
        raw_queries = [
            section.get("image_query", ""),
            section.get("image_query_2", ""),
            section.get("image_query_3", ""),
            section.get("image_query_4", ""),
        ]
        queries = []
        for raw in raw_queries:
            detail = _clean_visual_query(raw)
            # Discard abstract/unrelated query fragments instead of showing random stock.
            if not detail:
                continue
            q = f"{anchor} {detail}"
            if q.lower() not in [x.lower() for x in queries]:
                queries.append(q)

        # Topic-specific visual beats take priority for Navdurga / Shailputri.
        if anchor == "Maa Shailputri":
            if any(t in section_text for t in ("bail", "bull", "nandi", "नंदी", "वृषभ")):
                queries.insert(0, "Maa Shailputri riding Nandi bull")
            elif any(t in section_text for t in ("trishul", "त्रिशूल")):
                queries.insert(0, "Maa Shailputri holding trident")
            elif any(t in section_text for t in ("kamal", "lotus", "कमल")):
                queries.insert(0, "Maa Shailputri holding lotus")
            else:
                queries.insert(0, "Maa Shailputri Navdurga goddess idol white clothes")
        elif anchor.startswith("Maa ") and anchor != "Maa Durga":
            queries.insert(0, f"{anchor} Navdurga goddess idol")
        else:
            queries.insert(0, f"{anchor} devotional idol")

        # Do not allow a generated query to turn into a generic unrelated fallback.
        queries = list(dict.fromkeys(q for q in queries if q.strip()))
        paths = []
        wanted = min(4, max(2, len(queries))) if is_shorts else 3
        for qi, query in enumerate(queries):
            if len(paths) >= wanted:
                break
            paths.extend(_fetch_images(
                query, sid, images_dir, count=1, orientation=orientation,
                img_num_start=qi, fallback_queries=safe_fallbacks
            ))

        if not paths:
            fallback_path = os.path.join(images_dir, f"section_{sid:02d}_fallback.png")
            _make_fallback_image(fallback_path)
            paths = [fallback_path]
            print(f"         ⚠ No matching {anchor} stock images found; using devotional fallback graphic.")

        image_map[sid] = paths
        print(f"         [{sid}] {anchor}: saved {len(paths)} topic-anchored image(s)")
    return image_map
