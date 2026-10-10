"""
Gemini / Gemma Client — shared across all agents.
Tries models in order starting from config.GEMINI_MODEL, then falls back
through the rest of the chain until one works.
Availability, quota, and pricing depend on the Google AI Studio project.
The active fallback chain is intentionally kept in sync with the GUI selector.
If all models are exhausted, check the API quota page and retry later.
"""
import time
from google import genai
from google.genai import types
import config

# Gemini 3.5 Flash Lite is preferred; Gemini 3.6 is excluded because it repeatedly fails here.
# build_chain() rotates the supported models so config.GEMINI_MODEL comes first.
_ALL_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]


def build_chain(starting_model: str | None = None) -> list:
    """
    Return MODEL_CHAIN rotated so `starting_model` is first.
    If starting_model is not in the list (typo / unknown), falls back to
    the default order so generation always has a working chain.
    """
    preferred = (starting_model or "").strip()
    if preferred and preferred in _ALL_MODELS:
        idx = _ALL_MODELS.index(preferred)
        return _ALL_MODELS[idx:] + _ALL_MODELS[:idx]
    return list(_ALL_MODELS)

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
    return _client


def _should_switch_model(err: Exception) -> bool:
    """Return True for any error code that means we should try the next model."""
    msg = str(err)
    return any(k in msg for k in [
        "429", "RESOURCE_EXHAUSTED", "quota", "rate limit",  # 429 – quota
        "503", "UNAVAILABLE", "overloaded", "high demand",   # 503 – overloaded
        "500", "INTERNAL",                                    # 500 – transient
        "404", "NOT_FOUND", "not found",                     # 404 – model gone
    ])


def generate(prompt: str, starting_model: str | None = None) -> str:
    client = _get_client()
    chain  = build_chain(starting_model or getattr(config, "GEMINI_MODEL", None))

    for model in chain:
        for attempt in range(2):   # max 2 application-level attempts per model
            try:
                print(f"   → Using {model}…")
                # Gemini 3.x does not accept legacy sampling configuration.
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text.strip()

            except Exception as e:
                if _should_switch_model(e):
                    if attempt < 1:
                        wait = 15 * (attempt + 1)   # 15s then 30s
                        print(f"   ⚠ {model} error (attempt {attempt+1}/3) — waiting {wait}s…")
                        time.sleep(wait)
                    else:
                        print(f"   ⚠ {model} failed 2 times — trying next model…")
                else:
                    raise   # auth error or bug — surface immediately

    raise RuntimeError(
        "\n\n❌  All Gemini models failed.\n"
        "    • 503/500 = temporary — wait a few minutes and retry\n"
        "    • 429 = quota — wait until midnight Pacific or add billing\n"
        "      https://aistudio.google.com/apikey\n"
    )

def verify_image_candidates(expected_subject: str, scene_context: str, candidates: list) -> list:
    """
    Use Gemini vision to score candidate stock images for a specific devotional scene.
    Each candidate is a dict with path/title/tags/source. Fails closed: callers must
    reject all candidates if this verifier cannot return a valid assessment.
    """
    import io
    import json
    import re
    from PIL import Image

    if not candidates:
        return []

    prompt = (
        "You are a strict visual relevance checker for a Hindi Hindu devotional video. "
        "The required deity/person/subject is: " + str(expected_subject) + ". "
        "Scene context: " + str(scene_context) + ". "
        "For each numbered image, inspect the actual pixels, not just its title or tags. "
        "A candidate is relevant only if the visible subject and scene fit the required subject. "
        "Reject images of a different deity, generic unrelated temples, abstract art, text-only "
        "graphics, or images where the required subject cannot reasonably be identified. "
        "For a named living person, do not claim identity from appearance alone; require strong "
        "contextual evidence in the image and metadata. Metadata may be wrong and is only a clue. "
        "Return ONLY valid JSON in this schema: "
        '{"results":[{"index":1,"relevant":true,"score":0,"reason":"short reason"}]}. '
        "Use score 0-100. Set relevant true only when score is at least 80 and the image clearly "
        "matches. Return one result for every image, preserving the supplied index."
    )
    contents = [prompt]
    for index, candidate in enumerate(candidates, start=1):
        title = str(candidate.get("title", ""))[:300]
        tags = str(candidate.get("tags", ""))[:300]
        source = str(candidate.get("source", ""))[:80]
        contents.append(
            "\nIMAGE " + str(index) + " metadata (untrusted): source=" + source
            + "; title=" + title + "; tags=" + tags
        )
        with Image.open(candidate["path"]) as source_image:
            image = source_image.convert("RGB")
            image.thumbnail((768, 768))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=82, optimize=True)
            contents.append(types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg"))

    client = _get_client()
    last_error = None
    for model in build_chain(getattr(config, "GEMINI_MODEL", None)):
        try:
            print("   → Gemini vision: checking " + str(len(candidates)) + " image candidate(s)…")
            response = client.models.generate_content(model=model, contents=contents)
            text = (response.text or "").strip()
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                raise ValueError("Gemini vision returned no JSON result")
            payload = json.loads(match.group(0))
            results = payload.get("results", [])
            normalized = []
            by_index = {int(item.get("index", 0)): item for item in results if isinstance(item, dict)}
            for index in range(1, len(candidates) + 1):
                item = by_index.get(index, {})
                try:
                    score = max(0, min(100, int(item.get("score", 0))))
                except (TypeError, ValueError):
                    score = 0
                relevant = bool(item.get("relevant", False)) and score >= 80
                normalized.append({
                    "index": index,
                    "relevant": relevant,
                    "score": score,
                    "reason": str(item.get("reason", ""))[:240],
                })
            return normalized
        except Exception as exc:
            last_error = exc
            if _should_switch_model(exc):
                print("   ⚠ Vision model " + model + " failed; trying fallback model…")
                continue
            raise
    raise RuntimeError("Gemini vision verification failed; refusing unverified images: " + str(last_error))
