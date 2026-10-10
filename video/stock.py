"""Stock image downloader for YT Agent AI — Pixabay API."""
import os
import re
import io
import json
import shutil
import hashlib
import tempfile
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
         "Maa Shailputri", ["Maa Shailputri goddess idol", "Shailputri Mata Navdurga", "Maa Shailputri white clothes Nandi"]),
        (("brahmacharini", "ब्रह्मचारिणी"), "Maa Brahmacharini",
         ["Maa Brahmacharini Navdurga", "Brahmacharini Mata idol", "Maa Brahmacharini holding jap mala kamandalu"]),
        (("chandraghanta", "चंद्रघंटा"), "Maa Chandraghanta",
         ["Maa Chandraghanta Navdurga", "Chandraghanta Mata idol", "Maa Chandraghanta riding tiger bell"]),
        (("kushmanda", "कूष्मांडा", "कुष्मांडा"), "Maa Kushmanda",
         ["Maa Kushmanda Navdurga", "Kushmanda Mata idol", "Maa Kushmanda goddess idol"]),
        (("skandamata", "स्कंदमाता", "स्कन्दमाता"), "Maa Skandamata",
         ["Maa Skandamata Navdurga", "Skandamata Mata idol", "Maa Skandamata with child Kartikeya"]),
        (("katyayani", "कात्यायनी"), "Maa Katyayani",
         ["Maa Katyayani Navdurga", "Katyayani Mata idol", "Maa Katyayani goddess idol"]),
        (("kalaratri", "कालरात्रि", "कालरात्री"), "Maa Kalaratri",
         ["Maa Kalaratri Navdurga", "Kalaratri Mata idol", "Maa Kalaratri goddess idol"]),
        (("mahagauri", "महागौरी"), "Maa Mahagauri",
         ["Maa Mahagauri Navdurga", "Mahagauri Mata idol", "Maa Mahagauri goddess idol"]),
        (("siddhidatri", "सिद्धिदात्री"), "Maa Siddhidatri",
         ["Maa Siddhidatri Navdurga", "Siddhidatri Mata idol", "Maa Siddhidatri goddess idol"]),
        (("premanand", "प्रेमानंद"), "Premanand Ji Maharaj",
         ["Premanand Ji Maharaj satsang", "Premanand Maharaj portrait", "Vrindavan Premanand Ji Maharaj"]),
        (("krishna", "radha", "कृष्ण", "राधा", "वृंदावन", "गीता"),
         "Radha Krishna", ["Radha Krishna devotional", "Lord Krishna flute", "Vrindavan Krishna temple"]),
        (("shri ram", "lord ram", "rama", "रामायण", "श्रीराम", "प्रभु राम", "अयोध्या"),
         "Lord Rama", ["Lord Rama bow arrow", "Shri Ram Darbar idol", "Ayodhya Ram temple"]),
        (("vishnu", "narayan", "विष्णु", "नारायण", "दशावतार"),
         "Lord Vishnu", ["Lord Vishnu four arms", "Vishnu shankh chakra", "Narayan deity idol"]),
        (("ganesh", "ganesha", "गणेश", "गणपति", "विनायक"),
         "Lord Ganesha", ["Lord Ganesha idol", "Ganesha modak mouse", "Ganesh puja"]),
        (("surya dev", "surya", "सूर्य देव", "सूर्यनारायण"),
         "Surya Dev", ["Surya Dev Hindu deity", "Surya Narayan temple", "Surya puja Hindu"]),
        (("shani dev", "shani", "शनिदेव", "शनि देव"),
         "Shani Dev", ["Shani Dev idol", "Shani temple deity", "Shani puja Hindu"]),
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
        (("durga", "दुर्गा", "navratri", "नवरात्रि", "देवी", "शक्ति", "jai mata di", "जय माता दी", "mata rani", "माता रानी", "sherawali", "शेरावाली", "jagdambe", "जगदम्बे"),
         "Maa Durga", ["Maa Durga goddess idol", "Durga Mata lion", "Navratri Durga puja"]),
    ]
    for tokens, anchor, fallbacks in profiles:
        if any(token in source for token in tokens):
            return anchor, fallbacks
    return "Hindu devotional", ["Hindu deity idol devotional", "Hindu temple deity statue", "Hindu puja altar"]


def _clean_visual_query(query: str) -> str:
    """Remove vague cinematic wording so the search focuses on visible subjects."""
    query = _simplify_query(str(query or ""))
    query = re.sub(r"\b(cosmos|stars|galaxy|shocked person|human reaction|abstract art|light breaking through darkness)\b", " ", query, flags=re.I)
    return re.sub(r"\s+", " ", query).strip(" -,")


def _strip_html(value) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).replace("&nbsp;", " ").strip()


def _pixabay_candidates(query: str, orientation: str) -> list:
    api_key = getattr(config, "PIXABAY_API_KEY", "")
    if not api_key or api_key.startswith("YOUR_"):
        return []
    try:
        hits = _search_pixabay(api_key, query, orientation, per_page=12)
    except Exception as exc:
        print("   ⚠ Pixabay search error: " + str(exc))
        return []
    return [{
        "source": "Pixabay",
        "url": item.get("largeImageURL") or item.get("webformatURL") or "",
        "page_url": item.get("pageURL", ""),
        "title": item.get("tags", ""),
        "tags": item.get("tags", ""),
        "credit": item.get("user", ""),
        "license": "Pixabay Content License",
    } for item in hits if item.get("largeImageURL") or item.get("webformatURL")]


def _wikimedia_candidates(query: str) -> list:
    """Search Wikimedia Commons and keep only reusable, commercial-friendly licenses."""
    endpoint = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": "filetype:bitmap " + query,
        "gsrnamespace": 6,
        "gsrlimit": 12,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
        "format": "json",
    }
    try:
        response = requests.get(endpoint, params=params, timeout=20,
                                headers={"User-Agent": "YtAgentAI/1.0 (devotional video image licensing check)"})
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {}).values()
    except Exception as exc:
        print("   ⚠ Wikimedia Commons search error: " + str(exc))
        return []

    candidates = []
    for page in pages:
        info_list = page.get("imageinfo") or []
        if not info_list:
            continue
        info = info_list[0]
        meta = info.get("extmetadata") or {}
        license_name = _strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
        license_lower = license_name.lower()
        allowed = (
            "public domain" in license_lower or "cc0" in license_lower
            or (license_lower.startswith("cc by") and "nc" not in license_lower and "nd" not in license_lower)
        )
        if not allowed:
            continue
        candidates.append({
            "source": "Wikimedia Commons",
            "url": info.get("thumburl") or info.get("url") or "",
            "page_url": info.get("descriptionurl", ""),
            "title": _strip_html((meta.get("ImageDescription") or {}).get("value", "")) or page.get("title", ""),
            "tags": page.get("title", ""),
            "credit": _strip_html((meta.get("Artist") or {}).get("value", "")) or _strip_html((meta.get("Credit") or {}).get("value", "")),
            "license": license_name,
        })
    return [item for item in candidates if item.get("url")]


def _pexels_candidates(query: str, orientation: str) -> list:
    """Pexels is an optional fallback; it is used only when PEXELS_API_KEY is configured."""
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 12, "orientation": orientation},
            headers={"Authorization": api_key},
            timeout=20,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
    except Exception as exc:
        print("   ⚠ Pexels search error: " + str(exc))
        return []
    return [{
        "source": "Pexels",
        "url": (photo.get("src") or {}).get("large") or (photo.get("src") or {}).get("original") or "",
        "page_url": photo.get("url", ""),
        "title": photo.get("alt", ""),
        "tags": photo.get("alt", ""),
        "credit": photo.get("photographer", ""),
        "license": "Pexels License",
    } for photo in photos if (photo.get("src") or {}).get("large") or (photo.get("src") or {}).get("original")]


def _download_candidate(candidate: dict, path: str) -> bool:
    """Download, validate and normalize a candidate to JPEG before vision checking."""
    url = candidate.get("url", "")
    if not url:
        return False
    try:
        response = requests.get(url, timeout=30, stream=True, headers={"User-Agent": "YtAgentAI/1.0"})
        response.raise_for_status()
        chunks = []
        total = 0
        for chunk in response.iter_content(8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > 25 * 1024 * 1024:
                raise ValueError("image exceeds 25 MB limit")
            chunks.append(chunk)
        raw = b"".join(chunks)
        if len(raw) < 1024:
            return False
        with Image.open(io.BytesIO(raw)) as source:
            source.load()
            if source.width < 240 or source.height < 240:
                return False
            source.convert("RGB").save(path, format="JPEG", quality=90, optimize=True)
        return os.path.getsize(path) > 1024
    except Exception as exc:
        print("   ⚠ Candidate download/validation failed: " + str(exc))
        return False


def _provider_candidates(query: str, orientation: str) -> list:
    providers = [
        ("Pixabay", _pixabay_candidates),
        ("Wikimedia Commons", _wikimedia_candidates),
    ]
    if os.getenv("PEXELS_API_KEY", "").strip():
        providers.append(("Pexels", _pexels_candidates))
    for source_name, searcher in providers:
        results = searcher(query, orientation)
        if results:
            yield source_name, results


def download_images(script: dict, output_dir: str) -> dict:
    """
    For each scene, search up to five query variants across available sources.
    Gemini vision checks real image pixels and metadata; only candidates scoring
    >=80/100 are accepted. Failed or uncertain verification is rejected, never
    silently replaced with an unrelated deity or generic stock photo.
    """
    from agents.gemini_client import verify_image_candidates

    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    is_shorts = script.get("video_type") == "shorts"
    orientation = "portrait" if is_shorts else "landscape"
    anchor, safe_fallbacks = _topic_visual_profile(script)
    image_map = {}
    source_manifest = {}
    print("   🔎 Gemini-verified visual subject: " + anchor)
    print("   🔁 Up to 5 topic-specific searches; sources: Pixabay, Wikimedia Commons"
          + (", Pexels" if os.getenv("PEXELS_API_KEY", "").strip() else ""))

    for section in script.get("sections", []):
        sid = int(section.get("id", len(image_map) + 1))
        section_text = " ".join([
            str(section.get("title", "")),
            str(section.get("narration", "")),
            str(section.get("caption_text", "")),
        ]).strip()
        section_lower = section_text.lower()
        raw_queries = [
            section.get("image_query", ""),
            section.get("image_query_2", ""),
            section.get("image_query_3", ""),
            section.get("image_query_4", ""),
        ]

        if anchor == "Maa Shailputri":
            if any(t in section_lower for t in ("nandi", "नंदी", "वृषभ", "bull", "बैल")):
                preferred = "Maa Shailputri riding Nandi bull"
            elif any(t in section_lower for t in ("trishul", "त्रिशूल")):
                preferred = "Maa Shailputri holding trident"
            elif any(t in section_lower for t in ("lotus", "कमल")):
                preferred = "Maa Shailputri holding lotus"
            else:
                preferred = "Maa Shailputri Navdurga goddess idol white clothes"
        elif anchor.startswith("Maa ") and anchor != "Maa Durga":
            preferred = anchor + " Navdurga goddess idol"
        else:
            preferred = anchor + " devotional idol"

        query_list = [preferred]
        for raw in raw_queries:
            detail = _clean_visual_query(raw)
            if detail:
                query_list.append(anchor + " " + detail)
        query_list.extend(anchor + " " + _clean_visual_query(q) for q in safe_fallbacks)
        queries = []
        for query in query_list:
            query = re.sub(r"\s+", " ", query).strip()
            if query and query.lower() not in [item.lower() for item in queries]:
                queries.append(query)
        queries = queries[:5]

        wanted = 4 if is_shorts else 3
        accepted_paths = []
        used_digests = set()
        attempt_count = 0

        with tempfile.TemporaryDirectory(prefix="verify_scene_", dir=images_dir) as temp_dir:
            for query in queries:
                if len(accepted_paths) >= wanted or attempt_count >= 5:
                    break
                attempt_count += 1
                print("      🔍 Search " + str(attempt_count) + "/5: " + query)
                found_for_query = False

                for source_name, results in _provider_candidates(query, orientation):
                    downloaded = []
                    for idx, candidate in enumerate(results[:8], start=1):
                        candidate_path = os.path.join(temp_dir, "candidate_" + str(idx) + ".jpg")
                        if _download_candidate(candidate, candidate_path):
                            downloaded.append({**candidate, "path": candidate_path})
                    if not downloaded:
                        continue

                    try:
                        checks = verify_image_candidates(
                            expected_subject=anchor,
                            scene_context=section_text or section.get("title", ""),
                            candidates=downloaded,
                        )
                    except Exception as exc:
                        print("      ⚠ Gemini verification unavailable; rejecting unverified "
                              + source_name + " candidates: " + str(exc))
                        continue

                    approved = [
                        (downloaded[item["index"] - 1], item)
                        for item in checks
                        if item.get("relevant") and 1 <= item.get("index", 0) <= len(downloaded)
                    ]
                    approved.sort(key=lambda pair: pair[1].get("score", 0), reverse=True)
                    chosen = None
                    chosen_check = None
                    for candidate, check in approved:
                        with open(candidate["path"], "rb") as image_file:
                            digest = hashlib.sha256(image_file.read()).hexdigest()
                        if digest not in used_digests:
                            chosen, chosen_check = candidate, check
                            used_digests.add(digest)
                            break
                    if chosen is None:
                        print("      ✗ Gemini rejected all " + source_name + " candidates for this query")
                        continue

                    final_name = "section_" + str(sid).zfill(2) + "_img" + str(len(accepted_paths) + 1).zfill(2) + ".jpg"
                    final_path = os.path.join(images_dir, final_name)
                    shutil.copy2(chosen["path"], final_path)
                    accepted_paths.append(final_path)
                    source_manifest[os.path.relpath(final_path, output_dir)] = {
                        "source": chosen.get("source", source_name),
                        "source_page": chosen.get("page_url", ""),
                        "source_title": chosen.get("title", ""),
                        "credit": chosen.get("credit", ""),
                        "license": chosen.get("license", ""),
                        "search_query": query,
                        "gemini_score": chosen_check.get("score", 0),
                        "gemini_reason": chosen_check.get("reason", ""),
                    }
                    print("      ✓ Accepted " + source_name + " image (Gemini score "
                          + str(chosen_check.get("score", 0)) + "/100)")
                    found_for_query = True
                    break

                if not found_for_query:
                    print("      ✗ No verified image on this attempt; trying a new query/source")

        if not accepted_paths:
            if anchor != "Hindu devotional":
                raise RuntimeError(
                    "No verified topic-matched image found for '" + anchor + "' in section "
                    + str(sid) + " after up to 5 query attempts. Rendering stopped to avoid "
                    "showing the wrong deity. Check Gemini/Pixabay connectivity and quotas. "
                    "Optional: set PEXELS_API_KEY to enable Pexels fallback."
                )
            fallback_path = os.path.join(images_dir, "section_" + str(sid).zfill(2) + "_fallback.png")
            _make_fallback_image(fallback_path)
            accepted_paths = [fallback_path]
            print("      ⚠ Generic devotional fallback graphic used for an unspecified subject.")

        image_map[sid] = accepted_paths
        print("         [" + str(sid) + "] " + anchor + ": " + str(len(accepted_paths))
              + " verified image(s)")

    manifest_path = os.path.join(output_dir, "image_sources.json")
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(source_manifest, manifest_file, ensure_ascii=False, indent=2)
    print("   📄 Source/license manifest saved: " + manifest_path)
    return image_map
