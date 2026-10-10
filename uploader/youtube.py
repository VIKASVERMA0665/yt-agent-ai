"""
YouTube Uploader
Authenticates with the YouTube Data API v3 and uploads the final video.
"""
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import config


# Anchor credentials to the repository, not the process working directory.
# Scheduled tasks often start with a different working directory.
_REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(_REPO_DIR, "youtube_token.pickle")


def _repo_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(_REPO_DIR, path)


def _get_service():
    """Return an authenticated YouTube service object."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)
        except (OSError, pickle.PickleError, EOFError, AttributeError, ValueError) as exc:
            print(f"   ⚠ Saved YouTube token could not be read; re-authorizing: {exc}")
            creds = None

    # Refresh an expired token silently when Google provided a refresh token.
    # Only open the browser when no usable token exists or refresh is impossible.
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
            print("   ✓ Saved YouTube login refreshed; no browser login needed.")
        except Exception as exc:
            print(f"   ⚠ Saved YouTube login could not refresh; opening authorization: {exc}")
            creds = None

    if not creds or not creds.valid:
        client_secret_path = _repo_path(config.YOUTUBE_CLIENT_SECRET)
        if not os.path.exists(client_secret_path):
            raise FileNotFoundError(
                f"YouTube OAuth file not found: {client_secret_path}\n"
                "Follow the setup guide to create it in Google Cloud Console."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path, config.YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(script: dict, video_path: str) -> str:
    """
    Uploads the video with auto-generated title, description, and tags.
    Returns the public YouTube URL.
    """
    youtube = _get_service()

    description = (
        script.get("description", "") + "\n\n"
        + "─────────────────────────────\n"
        + "Subscribe for new explainers every week!\n"
        + "─────────────────────────────\n"
        + " ".join(f"#{t}" for t in script.get("tags", []))
    )

    body = {
        "snippet": {
            "title":       script["title"],
            "description": description,
            "tags":        script.get("tags", []),
            "categoryId":  config.VIDEO_CATEGORY_ID,
        },
        "status": {
            "privacyStatus":            config.VIDEO_PRIVACY,
            "selfDeclaredMadeForKids":  False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,   # 5 MB chunks
    )

    insert_req = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    print("   → Uploading…")
    response = None
    while response is None:
        status, response = insert_req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   → {pct}% uploaded", end="\r")

    print()
    video_id = response["id"]
    return f"https://www.youtube.com/watch?v={video_id}"
