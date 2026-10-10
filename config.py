import os

# Load a simple project-local .env file without requiring an extra dependency.
# Existing process environment variables always take precedence.
def _load_project_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError as exc:
        print(f"Warning: could not read .env file: {exc}")


_load_project_env()

# ─────────────────────────────────────────────────────────────────────────────
#  YT Agent AI — Configuration
#  Copy this file as-is. Fill in your API keys below (or use env vars).
#  All settings are documented. Change only what you need.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────
#  API Keys (check provider quotas and current pricing)
# ─────────────────────────────────────────
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY",     "YOUR_GEMINI_API_KEY")
PIXABAY_API_KEY    = os.getenv("PIXABAY_API_KEY",    "YOUR_PIXABAY_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_KEY")  # optional

# ─────────────────────────────────────────
#  Your Channel Identity
#  The more specific you are, the better the AI's topic suggestions.
# ─────────────────────────────────────────
CHANNEL_DESCRIPTION = """
A Hindi devotional YouTube channel focused on Hindu bhakti, bhajans, mantras, aarti, chalisa,
Premanand Ji Maharaj satsang, Krishna bhakti, Mahadev bhakti, Hanuman bhakti, Maa Durga,
Shri Ram, Vishnu and other Sanatan devotional topics.
Create engaging Hindi/Hinglish devotional videos that are respectful, spiritual, family-friendly,
and suitable for viewers seeking bhakti, peace, motivation and spiritual wisdom.
Target audience: Hindi-speaking devotees and families interested in Sanatan Dharma and devotional content.
"""
CHANNEL_NAME = "Bhakti Dhun"   # shown on-screen and in upload metadata

# ─────────────────────────────────────────
#  Voice (Edge TTS — free, no API key)
#  Bhakti Dhun requires Hindi female narration only. All pipeline entry points
#  enforce this voice so scheduled jobs cannot silently switch to a male voice.
# ─────────────────────────────────────────
VOICE_ID    = "hi-IN-SwaraNeural"
VOICE_RATE  = "-2%"     # natural devotional narration speed
VOICE_PITCH = "+0Hz"    # keep the natural neural-voice pitch

# ─────────────────────────────────────────
#  AI Model
#  Starting model for the fallback chain — the system auto-switches
#  through all models below if quota or errors are hit.
#  Change this in the GUI under Settings → AI Model, or here directly.
#  Models supported by agents/gemini_client.py:
#    gemini-3.6-flash       — preferred
#    gemini-3.5-flash-lite  — lightweight fallback
#    gemini-2.5-flash       — final fallback (access may vary by project)
#  Check Google AI Studio for current quota and pricing.
GEMINI_MODEL = "gemini-3.6-flash"

# ─────────────────────────────────────────
#  Video Dimensions
# ─────────────────────────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS    = 24

# YouTube Shorts dimensions (9:16 vertical)
SHORTS_WIDTH  = 1080
SHORTS_HEIGHT = 1920
SHORTS_FPS    = 30

# ─── Visual Style ───────────────────────
# Ken Burns effect: how much to zoom/pan each image
KB_ZOOM_START = 1.00    # starting scale (1.0 = no zoom)
KB_ZOOM_END   = 1.10    # ending scale   (1.1 = 10% zoom in)

# Image crossfade duration (seconds)
# 0.0 = instant cut  |  0.5 = snappy  |  0.7 = smooth  |  1.2 = dreamy
CROSSFADE_DURATION = 0.7

# Normal video B-roll cycling
BROLL_INTERVAL  = 10.0   # seconds each image stays on screen
BROLL_XFADE_DUR =  1.2   # crossfade duration (must be < BROLL_INTERVAL)

# Render quality preset (ffmpeg libx264)
# "ultrafast" = fastest/largest  |  "veryfast" = recommended  |  "medium" = best quality
RENDER_PRESET = "ultrafast"

# Overlay opacity: lower = more image visible but text harder to read (0–1)
OVERLAY_OPACITY = 0.62

# Colour palette — customise to match your brand
COLORS = {
    "background": (10,  10,  20),
    "overlay":    (0,   0,   0),
    "primary":    (245, 158, 11),    # saffron
    "accent":     (180, 83, 9),      # deep saffron
    "highlight":  (251, 191, 36),   # golden
    "white":      (255, 255, 255),
    "light":      (199, 210, 254),   # indigo-200
    "success":    (52,  211, 153),
    "red":        (239,  68,  68),
}

# Fonts — add your own .ttf paths for best results; system falls back gracefully
FONT_PATHS = {
    "bold":    [
        "C:/Windows/Fonts/Nirmala.ttc",
        "C:/Windows/Fonts/Impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "C:/Windows/Fonts/Nirmala.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "light":   [
        "C:/Windows/Fonts/segoeuil.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}

# ─────────────────────────────────────────
#  Review Server
# ─────────────────────────────────────────
REVIEW_PORT = 5050

# ─────────────────────────────────────────
#  YouTube Upload
# ─────────────────────────────────────────
YOUTUBE_CLIENT_SECRET = "client_secret.json"   # OAuth credentials file (see SETUP.md)
YOUTUBE_SCOPES        = ["https://www.googleapis.com/auth/youtube.upload"]
VIDEO_CATEGORY_ID     = "22"       # 22 = People & Blogs
VIDEO_PRIVACY         = "unlisted" # Initial test uploads stay unlisted; change to "public" after review.

# ─────────────────────────────────────────
#  Background Music
#  Drop MP3/WAV files into the  music library/  folder.
#  Tracks are shuffled and looped automatically to match video length.
# ─────────────────────────────────────────
MUSIC_ENABLED     = True
MUSIC_VOLUME      = 0.12          # 0.0–1.0  (0.12 = subtle underscore)
MUSIC_LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "music library")

# ─────────────────────────────────────────
#  Paths  (do not change unless you know what you're doing)
# ─────────────────────────────────────────
OUTPUT_DIR   = "output"
IMAGES_DIR   = "output/images"
