"""
Notion OAuth flow — mirrors the Google OAuth pattern exactly.

Step 1: GET /auth/notion/url        → returns the Notion authorization URL.
Step 2: User authorises            → Notion redirects to /auth/notion/callback.
Step 3: Backend exchanges code for a token, saves the integration, and
        renders success.  The UI then fetches the database list from
        GET /sync/notion/databases so the user can pick one.
"""

from __future__ import annotations

import logging
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.tasks import get_or_create_default_user
from app.core.config import settings
from app.core.database import get_db
from app.services import integration_service
from app.services.notion_service import DEFAULT_NOTION_SETTINGS

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

NOTION_AUTH_URI = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URI = "https://api.notion.com/v1/oauth/token"

_oauth_states: dict[str, int] = {}


class OAuthUrlResponse(BaseModel):
    url: str


@router.get("/auth/notion/url", response_model=OAuthUrlResponse)
def get_notion_auth_url(db: Session = Depends(get_db)):
    if not settings.NOTION_CLIENT_ID:
        return OAuthUrlResponse(url="")

    user = get_or_create_default_user(db)
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = user.id

    params = {
        "client_id": settings.NOTION_CLIENT_ID,
        "redirect_uri": settings.NOTION_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "owner": "user",
        "state": state,
    }
    url = f"{NOTION_AUTH_URI}?{urllib.parse.urlencode(params)}"
    return OAuthUrlResponse(url=url)


@router.get("/auth/notion/callback")
async def handle_notion_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.error("Notion OAuth denied: %s", error)
        return _oauth_html("error", "Authorization denied", f"Notion returned: {error}")

    if not code or not state:
        return _oauth_html("error", "Missing parameters", "No authorization code received.")

    user_id = _oauth_states.pop(state, None)
    if user_id is None:
        return _oauth_html("error", "Session expired", "Please try connecting again.")

    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET:
        return _oauth_html("error", "Not configured", "Notion OAuth is not configured on the server.")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                NOTION_TOKEN_URI,
                auth=(settings.NOTION_CLIENT_ID, settings.NOTION_CLIENT_SECRET),
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.NOTION_OAUTH_REDIRECT_URI,
                },
            )
            data = resp.json()

            if "error" in data:
                logger.error("Notion token exchange error: %s", data["error"])
                return _oauth_html("error", "Token failed", f"Notion rejected the code: {data['error']}")

            access_token = data.get("access_token")
            if not access_token:
                return _oauth_html("error", "No token", "No access token in Notion's response.")

            integration_service.save_integration_config(
                db=db,
                user_id=user_id,
                provider="notion",
                access_token=access_token,
                refresh_token=None,
                expires_in_seconds=31536000,
                settings=dict(DEFAULT_NOTION_SETTINGS),
            )

            logger.info("Notion OAuth connected for user %d", user_id)
            return _oauth_html("success", "Connected to Notion!", "Pick a database in sync settings to start syncing.")

    except Exception as e:
        logger.error("Notion OAuth exception: %s", e)
        return _oauth_html("error", "Connection failed", str(e))


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
