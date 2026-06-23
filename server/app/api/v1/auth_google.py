import json
import logging
import os
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.tasks import get_or_create_default_user
from app.core.database import get_db
from app.services import integration_service
from app.services.constants import DEFAULT_SYNC_SETTINGS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# --- Load Google OAuth credentials from client_secret.json ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SECRET_PATH = os.path.join(_PROJECT_ROOT, "secret", "client_secret.json")

with open(_SECRET_PATH) as f:
    _web = json.load(f)["web"]

GOOGLE_CLIENT_ID = _web["client_id"]
GOOGLE_CLIENT_SECRET = _web["client_secret"]
GOOGLE_REDIRECT_URI = _web["redirect_uris"][0]
GOOGLE_AUTH_URI = _web["auth_uri"]
GOOGLE_TOKEN_URI = _web["token_uri"]

GOOGLE_SCOPES = " ".join([
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
])

_oauth_states: dict[str, int] = {}


# ── Schemas ──────────────────────────────────────────────────────────────

class OAuthUrlResponse(BaseModel):
    url: str


# ── Step 1: Generate the OAuth URL ───────────────────────────────────────

@router.get("/auth/google/url", response_model=OAuthUrlResponse)
def get_google_auth_url(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = user.id

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URI}?{urllib.parse.urlencode(params)}"
    return OAuthUrlResponse(url=url)


# ── Step 2: Google redirects here after user authorizes ──────────────────

@router.get("/auth/google/callback")
async def handle_google_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.error("Google OAuth denied: %s", error)
        return _oauth_html("error", "Authorization denied", f"Google returned: {error}")

    if not code or not state:
        return _oauth_html("error", "Missing parameters", "No authorization code received.")

    user_id = _oauth_states.pop(state, None)
    if user_id is None:
        return _oauth_html("error", "Session expired", "Please try connecting again.")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(GOOGLE_TOKEN_URI, data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            data = resp.json()

            if "error" in data:
                logger.error("Google token exchange error: %s", data["error"])
                return _oauth_html("error", "Token failed", f"Google rejected the code: {data['error']}")

            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)

            if not access_token:
                return _oauth_html("error", "No token", "No access token in Google's response.")

            integration_service.save_integration_config(
                db=db,
                user_id=user_id,
                provider="google",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in_seconds=expires_in,
                settings={"scopes": GOOGLE_SCOPES, "sync_settings": DEFAULT_SYNC_SETTINGS},
            )

            logger.info("Google OAuth connected for user %d", user_id)
            return _oauth_html("success", "Connected to Google!", "You may close this window.")

    except Exception as e:
        logger.error("Google OAuth exception: %s", e)
        return _oauth_html("error", "Connection failed", str(e))


# ── Helper: render HTML pages for the OAuth popup ────────────────────────

def _oauth_html(kind: str, title: str, message: str) -> HTMLResponse:
    if kind == "success":
        icon = "✅"
        title_color = "#38bdf8"
        auto_close = True
    else:
        icon = "❌"
        title_color = "#ef4444"
        auto_close = False

    auto_close_script = '<script>setTimeout(function(){window.close()},1500)</script>' if auto_close else ""

    return HTMLResponse(f"""<!DOCTYPE html>
<html>
<head><title>dopapal-oauth-{kind}</title></head>
<body style="font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#1a1a2e;color:#e0e0e0">
<div style="text-align:center;padding:2rem">
<div style="font-size:3rem;margin-bottom:1rem">{icon}</div>
<h1 style="color:{title_color};margin:0 0 0.5rem">{title}</h1>
<p style="color:#94a3b8">{message}</p>
</div>
{auto_close_script}
</body>
</html>""")
