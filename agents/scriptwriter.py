"""
Script Writer Agent — uses shared Gemini client with model fallback chain.
"""
import json
import re
from agents.gemini_client import generate


def write_script(research: dict, video_type: str = "normal") -> dict:
    """
    Generates a narrated script for a YouTube video or YouTube Short.
    video_type: "normal" (6-8 min, 9 sections) | "shorts" (50-60 sec, 3 sections)
    Returns structured JSON with sections, each containing narration + image_query.
    """
    if video_type == "shorts":
        return _write_shorts_script(research)

    key_points_str = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(research["key_points"]))

    prompt = f"""You are the lead scriptwriter for a viral Hindi devotional YouTube channel. Write the narration in natural spoken Hindi using Devanagari script (हिंदी), suitable for a warm human devotional voice.
Use English only when it is genuinely part of a proper name or unavoidable term. Do NOT write Romanized Hindi such as
"bhakti", "aap", "kya", "kyunki" inside narration. The narration must sound like a real Hindi speaker, not a translated article.

Video topic: {research["topic"]}
Title: {research["video_title"]}
Core hook question: {research.get("hook_question", "")}
Key points to cover:
{key_points_str}

Write a GRIPPING, cinematic 6-8 minute Hindi devotional script. Non-negotiable rules:

PACING RULES (keep devotional viewers engaged):
- - Section 4 MUST open with a devotional re-hook such as "Lekin yahan kahani ek aisa mod leti hai..." or "Rukiye, asli rahasya to ab shuru hota hai..."
- Section 6 MUST connect the spiritual teaching to everyday life with a fresh re-hook.
- Use OPEN LOOPS: raise a meaningful spiritual question early and answer it later.
- Vary sentence length and keep narration natural for Hindi voice synthesis.
- Use short and medium sentences with natural commas and sentence endings.
- Use proper punctuation throughout: comma (,), question mark (?), exclamation (!), and Hindi danda (।).
- Add commas where a human speaker would naturally breathe; do not write long unpunctuated paragraphs.
- Every narration sentence must end with appropriate punctuation.
- Use respectful devotional language. Do not present unverifiable miracles as established fact; frame them as traditional beliefs or scripture-based stories.

VISUAL RULES (STRICT):
- Every image query MUST explicitly name the exact deity/person/festival in the video topic.
- If the topic names Maa Shailputri, every query must say "Maa Shailputri" or "Shailputri Mata"; show her idol/form, white attire, Nandi bull, trident or lotus only when relevant.
- Never suggest random cosmos, generic temples, unrelated gods/goddesses, generic human reactions, or abstract images that do not depict the exact topic.
- For each section create 3 distinct but TOPIC-MATCHED searches: deity/form wide view, a specific attribute/ritual close-up, and another accurate depiction of the same deity.
- Query strings must be concrete searchable visual subjects, not cinematic instructions or abstract metaphors.

Respond with ONLY a valid JSON object. No markdown fences, no extra text:

{{
  "title": "{research['video_title']}",
  "description": "{research.get('description', '')}",
  "tags": {json.dumps(research.get('tags', []))},
  "sections": [
    {{
      "id": 1,
      "section_type": "hook",
      "title": "Short, punchy on-screen title — NOT 'The Hook'",
      "narration": "Open with an impossible statement or visceral question that stops the scroll. 3-4 sentences. End on an open question that section 2 will tease but section 5 will answer.",
      "image_query": "dramatic wide establishing shot matching the topic",
      "image_query_2": "close-up detail or human reaction shot",
      "image_query_3": "symbolic spiritual visual matching the devotional mood",
      "bullet_points": [],
      "caption_text": "Short punchy caption shown on screen",
      "duration_seconds": 25
    }},
    {{
      "id": 2,
      "section_type": "intro",
      "title": "On-screen title — NOT 'Setting the Stage'",
      "narration": "Establish context and scale. Pose the open-loop question explicitly: 'Here is the question we need to answer: [question].' Promise the viewer the answer is coming and it will change everything. 4-5 sentences.",
      "image_query": "temple, pilgrimage or sacred setting dramatic wide shot",
      "image_query_2": "devotee, sadhu or spiritual teacher close-up",
      "image_query_3": "scripture, temple architecture or spiritual-symbol concept",
      "bullet_points": ["The spiritual question we will answer", "Why this teaching matters", "What people often misunderstand"],
      "caption_text": "What we'll explore today",
      "duration_seconds": 40
    }},
    {{
      "id": 3,
      "section_type": "content",
      "title": "On-screen title — NOT 'First Revelation'",
      "narration": "First deep explanation. Use a concrete analogy ('Imagine if…'). Build simple → complex. 5-7 sentences. End with a setup that makes section 4 feel inevitable.",
      "image_query": "specific concept matching this section — dramatic wide",
      "image_query_2": "close-up detail of the concept",
      "image_query_3": "abstract or metaphorical visual for the analogy used",
      "bullet_points": ["Core fact A", "Core fact B — the surprising part"],
      "caption_text": "The first mind-blowing fact",
      "duration_seconds": 70
    }},
    {{
      "id": 4,
      "section_type": "re_hook",
      "title": "On-screen title — a gear-shift title like 'But Wait.' or 'The Twist Nobody Sees'",
      "narration": "MANDATORY: Open with a re-hook line like 'But here's where it gets REALLY weird…' or 'Wait — everything I just said is only half the story.' Then deliver the counterintuitive twist. The viewer who almost dropped off at 90 seconds just got pulled back. 5-7 sentences.",
      "image_query": "dramatic reveal or twist — light breaking through darkness",
      "image_query_2": "shocked or awed human expression or reaction",
      "image_query_3": "abstract visual representing a paradigm shift",
      "bullet_points": ["What you thought was true", "What is actually true — the twist"],
      "caption_text": "Nothing is what it seems",
      "duration_seconds": 70
    }},
    {{
      "id": 5,
      "section_type": "content",
      "title": "On-screen title — NOT 'Going Deeper'",
      "narration": "The deeper layer. MANDATORY: answer the open-loop question posed in section 2 here. 'Remember the question I asked earlier? Here is the answer — and it's stranger than you imagined.' Then the implications. 5-7 sentences.",
      "image_query": "the answer or resolution concept — dramatic and clear",
      "image_query_2": "scripture verse, sacred symbol or devotional detail close-up",
      "image_query_3": "wide temple, pilgrimage or nature-spirituality shot",
      "bullet_points": ["The answer to the open question", "Implication A", "Implication B"],
      "caption_text": "The rabbit hole goes deeper",
      "duration_seconds": 70
    }},
    {{
      "id": 6,
      "section_type": "re_hook",
      "title": "On-screen title — a second gear-shift like 'And It Gets Worse.' or 'The Part Nobody Talks About'",
      "narration": "MANDATORY: Second re-hook at the 3-minute mark. Open with a sudden gear-shift: 'So why does any of this actually matter? Let me show you something that changes everything.' Then hit the real-world human stakes hard. 5-6 sentences.",
      "image_query": "devotees, family life or everyday Indian setting wide shot",
      "image_query_2": "prayer, diya, mala or devotional practice close-up",
      "image_query_3": "devotee hands in prayer or peaceful human expression",
      "bullet_points": ["Why this affects YOU personally", "The consequence most people ignore", "What happens if we do nothing"],
      "caption_text": "What this means for all of us",
      "duration_seconds": 65
    }},
    {{
      "id": 7,
      "section_type": "content",
      "title": "On-screen title — a philosophical or existential angle",
      "narration": "The spiritual dimension. Connect the teaching to a real human struggle, devotion, karma, dharma or inner peace. 4-6 sentences. End with a thoughtful devotional question that leads into the conclusion.",
      "image_query": "sunrise over temple, river ghat or peaceful pilgrimage landscape",
      "image_query_2": "lone human figure against vast landscape or sky",
      "image_query_3": "diya flame, meditation or symbolic spiritual light-and-shadow visual",
      "bullet_points": ["The big unanswered question", "What experts disagree on"],
      "caption_text": "The question that stays in every devotee's heart",
      "duration_seconds": 60
    }},
    {{
      "id": 8,
      "section_type": "conclusion",
      "title": "On-screen title — a satisfying payoff title",
      "narration": "Bring it home. Three punchy takeaways. Callback to the opening hook ('Remember how I asked…? Now you know.'). End with a direct question for the comments — one that every viewer has a personal answer to.",
      "image_query": "hope or breakthrough — light emerging from darkness",
      "image_query_2": "scripture or sacred object close-up revealing meaning",
      "image_query_3": "devotee walking toward temple sunrise or hopeful spiritual landscape",
      "bullet_points": ["Core truth #1 — punchy and memorable", "Core truth #2 — the twist payoff", "Core truth #3 — the call to think"],
      "caption_text": "What have we understood?",
      "duration_seconds": 50
    }},
    {{
      "id": 9,
      "section_type": "cta",
      "title": "On-screen title — e.g. 'Join the Journey'",
      "narration": "Aaj ki bhakti aur seekh agar aapke dil ko chhoo gayi ho, to channel ko subscribe karein aur comment mein likhein ki aap kis devta ya mantra se sabse zyada jude hue hain. Jai Shri Ram, Har Har Mahadev, Radhe Radhe.",
      "image_query": "temple illuminated at night, diya, stars",
      "image_query_2": "devotees gathered for satsang or aarti",
      "image_query_3": "peaceful temple or pilgrimage landscape wide shot",
      "bullet_points": [],
      "caption_text": "Nayi bhakti aur seekh ke liye jude rahiye",
      "duration_seconds": 18
    }}
  ]
}}

IMPORTANT:
- image_query / image_query_2 / image_query_3 must be VISUALLY DISTINCT from each other (wide → close → abstract).
- Use SPECIFIC Pixabay-friendly English search strings, 3-7 concrete words each (e.g. "Krishna temple devotional India", "diya aarti close up", "devotee praying temple").
- Do not use abstract instructions such as "dramatic wide establishing shot matching the topic"; name the actual subject to search for.
- Narration for sections 4 and 6 MUST start with the mandatory re-hook lines as described.
- The open-loop question from section 2 MUST be answered in section 5.
- Every narration field must contain COMPLETE, broadcast-ready sentences — no placeholders.
- The entire script must feel cinematic, devotional, emotional, respectful, human and broadcast-ready in Hindi/Hinglish. Do not imitate or claim to be written by any specific creator."""

    print("   → Writing script with Gemini...")
    raw = generate(prompt)
        raw = re.sub(r"^" + "`" * 3 + r"(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError(f"Scriptwriter returned no JSON.\n\nRaw:\n{raw[:600]}")

    script = json.loads(match.group())

    if "sections" not in script or len(script["sections"]) < 4:
        raise ValueError("Script returned too few sections.")

    return script


def _write_shorts_script(research: dict) -> dict:
    """
    Generates a tight 50-60 second YouTube Shorts script (3 sections, vertical format).
    """
    key_points_str = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(research["key_points"][:3]))

    prompt = f"""You are a viral Hindi devotional YouTube Shorts scriptwriter. You write punchy, emotional, respectful 50-60 second vertical devotional videos. Narration must be natural Hindi in Devanagari script, with commas, प्रश्नचिह्न, विस्मयादिबोधक and Hindi danda (।) used naturally. Do not write Romanized Hindi.

Video topic: {research["topic"]}
Title: {research["video_title"]}
Hook question: {research.get("hook_question", "")}
Key points:
{key_points_str}

Write a GRIPPING 50-60 second Hindi/Hinglish devotional Shorts script. Rules:
- Hooks in the FIRST 3 words — no slow intros
- Short, punchy sentences. Every second counts.
- Vertical video style: one idea per second
- End with a devotional thought, question or emotional takeaway that encourages follow/subscribe
- 3 sections ONLY: hook (10-12s), revelation (30-35s), cta (8-10s)
- Total narration must be 120-160 words maximum
- NEVER name the section in the title field — title is INTERNAL only, not shown on screen

Respond with ONLY a valid JSON object. No markdown fences, no extra text:

{{
  "title": "{research['video_title']} #Shorts",
  "description": "Short, punchy 2-sentence description for the Short.",
  "tags": {json.dumps(research.get('tags', []) + ["Shorts", "YouTubeShorts"])},
  "sections": [
    {{
      "id": 1,
      "section_type": "hook",
      "title": "hook_internal",
      "narration": "Open with a jaw-dropping 1-sentence statement. Then the question. 2-3 punchy sentences MAX. About 30-35 words.",
      "image_query": "exact deity named in topic full idol form",
      "image_query_2": "exact deity named in topic signature attribute close up",
      "image_query_3": "exact deity named in topic devotional worship scene",
      "image_query_4": "exact deity named in topic sacred symbol or scripture",
      "bullet_points": [],
      "caption_text": "",
      "duration_seconds": 12
    }},
    {{
      "id": 2,
      "section_type": "content",
      "title": "content_internal",
      "narration": "The core mind-blowing fact, explained in 3-4 punchy sentences. No fluff. Drive home the ONE key insight. About 80-90 words.",
      "image_query": "exact deity named in topic recognizable idol form",
      "image_query_2": "exact deity named in topic specific puja ritual",
      "image_query_3": "exact deity named in topic traditional attribute",
      "image_query_4": "exact deity named in topic temple idol close up",
      "bullet_points": [],
      "caption_text": "",
      "duration_seconds": 35
    }},
    {{
      "id": 3,
      "section_type": "cta",
      "title": "cta_internal",
      "narration": "Drop one final mind-bending teaser, then tell them to follow for aur aisi bhakti ki rochak kahaniyon. 15-20 words.",
      "image_query": "exact deity named in topic devotional idol",
      "image_query_2": "exact deity named in topic puja flowers diya",
      "image_query_3": "exact deity named in topic temple worship scene",
      "image_query_4": "exact deity named in topic scripture and mala",
      "bullet_points": [],
      "caption_text": "",
      "duration_seconds": 10
    }}
  ]
}}

IMPORTANT:
- Total narration across ALL sections: 120-160 words maximum
- Each section narration must be complete, broadcast-ready sentences
- Every image_query and image_query_2/3/4 must explicitly include the exact deity/person named by the topic; all must be specific, visual Pixabay search strings, never generic or unrelated
- title fields are INTERNAL labels only — they are never shown on screen"""

    print("   → Writing Shorts script with Gemini...")
    last_error = None
    script = None

    # Gemini may occasionally return a truncated or under-filled JSON response.
    # Retry once with an explicit correction instead of failing the whole video.
    for attempt in range(2):
        retry_note = ""
        if attempt:
            retry_note = (
                "\n\nCORRECTION REQUIRED: Your previous response did not contain exactly "
                "3 valid sections. Return a complete JSON object with exactly 3 sections: "
                "hook, content, cta. Do not add commentary or markdown."
            )
            print("   ⚠ Shorts script had too few sections; retrying Gemini once...")

        raw = generate(prompt + retry_note)
        raw = re.sub(r"^" + "`" * 3 + r"(?:json)?", "", raw).strip()
        raw = re.sub(r"`" + "`" * 2 + r"$", "", raw).strip()

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            last_error = "response contained no JSON object"
            continue

        try:
            candidate = json.loads(match.group())
        except json.JSONDecodeError as exc:
            last_error = f"invalid JSON: {exc}"
            continue

        sections = candidate.get("sections")
        if not isinstance(sections, list) or len(sections) < 3:
            count = len(sections) if isinstance(sections, list) else 0
            last_error = f"expected 3 sections, received {count}"
            continue

        # Keep the three-part Shorts structure consistent for downstream rendering.
        candidate["sections"] = sections[:3]
        script = candidate
        break

    if script is None:
        raise ValueError(
            "Gemini failed to return a valid 3-section Shorts script after 2 attempts "
            f"({last_error}). Check the Gemini response/model and retry."
        )

    # Tag it so the video creator knows
    script["video_type"] = "shorts"
    return script
