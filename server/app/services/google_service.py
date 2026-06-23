import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
import httpx

from app.models.integration import IntegrationToken
from app.services import integration_service
from app.services.task_service import ingest_from_raw_text
from app.services.constants import DEFAULT_SYNC_SETTINGS

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_TASKS_API = "https://tasks.googleapis.com/tasks/v1"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"

SYNC_INTERVAL_MINUTES = 15


def _load_google_creds() -> dict[str, str]:
    import json, os
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _secret = os.path.join(_root, "secret", "client_secret.json")
    with open(_secret) as f:
        _web = json.load(f)["web"]
    return {
        "client_id": _web["client_id"],
        "client_secret": _web["client_secret"],
    }


_creds: Optional[dict[str, str]] = None


def _get_creds() -> dict[str, str]:
    global _creds
    if _creds is None:
        _creds = _load_google_creds()
    return _creds



def get_token_entry(db: Session, user_id: int, provider: str = "google") -> Optional[IntegrationToken]:
    return db.query(IntegrationToken).filter(
        IntegrationToken.user_id == user_id,
        IntegrationToken.provider == provider,
    ).first()


def get_decoded_token(token: IntegrationToken) -> str:
    return integration_service.decrypt_token(token.access_token_enc)


def get_decoded_refresh_token(token: IntegrationToken) -> Optional[str]:
    if token.refresh_token_enc:
        return integration_service.decrypt_token(token.refresh_token_enc)
    return None


def refresh_access_token(db: Session, token: IntegrationToken) -> str:
    refresh_tok = get_decoded_refresh_token(token)
    if not refresh_tok:
        raise RuntimeError("No refresh token available for Google integration")

    creds = _get_creds()
    with httpx.Client() as client:
        resp = client.post(GOOGLE_TOKEN_URI, data={
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": refresh_tok,
            "grant_type": "refresh_token",
        })
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Token refresh failed: {data['error']}")

        new_access = data["access_token"]
        new_expires_in = data.get("expires_in", 3600)

        token.access_token_enc = integration_service.encrypt_token(new_access)
        token.expires_at = datetime.utcnow() + timedelta(seconds=new_expires_in)
        db.commit()

        return new_access


def get_valid_access_token(db: Session, user_id: int) -> str:
    token = get_token_entry(db, user_id)
    if not token:
        raise RuntimeError("Google not connected")

    if datetime.utcnow() >= token.expires_at:
        return refresh_access_token(db, token)

    return get_decoded_token(token)


def _google_get(url: str, access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    items: list[dict] = []
    page_token = None
    with httpx.Client(timeout=30) as client:
        while True:
            params: dict[str, Any] = {"maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return items



def fetch_tasks(access_token: str) -> list[dict]:
    lists = _google_get(f"{GOOGLE_TASKS_API}/users/@me/lists", access_token)
    all_tasks: list[dict] = []
    for tl in lists:
        tl_id = tl["id"]
        tl_title = tl.get("title", "Untitled")
        url = f"{GOOGLE_TASKS_API}/lists/{tl_id}/tasks"
        tasks = _google_get(url, access_token)
        for t in tasks:
            t["_list_title"] = tl_title
            t["_list_id"] = tl_id
        all_tasks.extend(tasks)
    return all_tasks


def fetch_calendar_events(access_token: str, days_ahead: int = 30) -> list[dict]:
    now = datetime.utcnow().isoformat() + "Z"
    later = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"
    url = f"{GOOGLE_CALENDAR_API}/calendars/primary/events"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "timeMin": now,
        "timeMax": later,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 250,
    }
    items: list[dict] = []
    page_token = None
    with httpx.Client(timeout=30) as client:
        while True:
            p: dict[str, Any] = dict(params)
            if page_token:
                p["pageToken"] = page_token
            resp = client.get(url, headers=headers, params=p)
            resp.raise_for_status()
            data = resp.json()
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return items


# ── Filtering helpers ──────────────────────────────────────────────────


def _parse_keywords(text: str) -> list[str]:
    return [kw.strip().lower() for kw in text.split(",") if kw.strip()]


def _has_any_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    for kw in keywords:
        if kw in lowered:
            return True
    return False


def _get_event_duration(event: dict) -> Optional[float]:
    start_str = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
    end_str = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date", "")
    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            return (end - start).total_seconds() / 60
        except ValueError:
            pass
    return None


def _should_sync_event(event: dict, settings: dict) -> bool:
    cal_settings = settings.get("calendar", {})
    if not cal_settings.get("enabled", True):
        return False

    if event.get("recurringEventId"):
        return False

    # Event type filter (default, focusTime, outOfOffice, workingLocation)
    event_type = event.get("eventType", "default")
    allowed_types = _parse_keywords(cal_settings.get("include_event_types", "default"))
    if event_type not in allowed_types:
        return False

    title = (event.get("summary") or "").strip()
    desc = (event.get("description") or "").strip()
    combined = f"{title} {desc}"

    include_kw = _parse_keywords(cal_settings.get("include_keywords", ""))
    exclude_kw = _parse_keywords(cal_settings.get("exclude_keywords", ""))
    min_duration = cal_settings.get("min_duration_minutes", 30)

    # Exclude keywords take priority
    if _has_any_keyword(title, exclude_kw):
        return False

    # Include keywords → always import
    if _has_any_keyword(combined, include_kw):
        return True

    # Has a description AND meets minimum duration → likely substantive
    duration = _get_event_duration(event)
    if desc and (duration is None or duration >= min_duration):
        return True

    return False


def _should_sync_gtask(gtask: dict, settings: dict) -> bool:
    task_settings = settings.get("tasks", {})
    if not task_settings.get("enabled", True):
        return False

    if gtask.get("status") == "completed" and not task_settings.get("include_completed", False):
        return False

    title = (gtask.get("title") or "").strip()
    if not title:
        return False

    due = gtask.get("due", "")
    if not due and not task_settings.get("include_no_due_date", True):
        return False

    return True


# ── Raw-text converters ────────────────────────────────────────────────

def _task_to_raw_text(gtask: dict) -> str:
    title = gtask.get("title", "").strip()
    notes = gtask.get("notes", "").strip()
    due = gtask.get("due", "")
    text = title
    if notes:
        text += f" — {notes}"
    if due:
        try:
            dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
            text += f", due {dt.strftime('%Y-%m-%d')}"
        except ValueError:
            pass
    return text if text else ""


def _event_to_raw_text(event: dict) -> str:
    summary = event.get("summary", "").strip()
    description = event.get("description", "").strip()
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
    text = summary
    if description:
        text += f" — {description}"
    if start:
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            text += f", due {dt.strftime('%Y-%m-%d')} at {dt.strftime('%H:%M')}"
        except ValueError:
            text += f", due {start}"
    return text if text else ""


# ── Sync implementations ───────────────────────────────────────────────

def _sync_tasks(db: Session, user_id: int, access_token: str, settings: dict) -> dict:
    synced_ids: set[str] = set(settings.get("synced_task_ids", {}))
    new_count = 0
    skipped = 0

    task_settings = settings.get("tasks", {})
    interest_tags = _parse_keywords(task_settings.get("interest_tag", ""))
    interest_tag_override = ", ".join(interest_tags) if interest_tags else None

    tasks = fetch_tasks(access_token)
    for gtask in tasks:
        gid = gtask.get("id")
        if not gid or gid in synced_ids:
            continue

        if not _should_sync_gtask(gtask, settings):
            skipped += 1
            continue

        raw = _task_to_raw_text(gtask)
        if not raw:
            skipped += 1
            continue

        try:
            ingest_from_raw_text(db=db, user_id=user_id, raw_text=raw, source_type="google_tasks", interest_tag_override=interest_tag_override)
            synced_ids.add(gid)
            new_count += 1
            logger.info("Synced Google task: %s", gtask.get("title", "(untitled)"))
        except Exception as e:
            logger.warning("Failed to ingest Google task %s: %s", gid, e)

    settings["synced_task_ids"] = list(synced_ids)
    return {"type": "tasks", "new": new_count, "skipped": skipped, "total": len(tasks)}


def _sync_events(db: Session, user_id: int, access_token: str, settings: dict) -> dict:
    synced_ids: set[str] = set(settings.get("synced_event_ids", {}))
    new_count = 0
    skipped = 0

    cal_settings = settings.get("calendar", {})
    interest_tags = _parse_keywords(cal_settings.get("interest_tag", ""))
    interest_tag_override = ", ".join(interest_tags) if interest_tags else None

    events = fetch_calendar_events(access_token)
    for event in events:
        eid = event.get("id")
        if not eid or eid in synced_ids:
            continue

        if not _should_sync_event(event, settings):
            skipped += 1
            continue

        raw = _event_to_raw_text(event)
        if not raw:
            skipped += 1
            continue

        try:
            ingest_from_raw_text(db=db, user_id=user_id, raw_text=raw, source_type="calendar", interest_tag_override=interest_tag_override)
            synced_ids.add(eid)
            new_count += 1
            logger.info("Synced Calendar event: %s", event.get("summary", "(untitled)"))
        except Exception as e:
            logger.warning("Failed to ingest Calendar event %s: %s", eid, e)

    settings["synced_event_ids"] = list(synced_ids)
    return {"type": "events", "new": new_count, "skipped": skipped, "total": len(events)}


def sync_google(db: Session, user_id: int, sync_settings: dict | None = None) -> dict[str, Any]:
    logger.info("Starting Google sync for user %d", user_id)

    token = get_token_entry(db, user_id)
    if not token:
        return {"success": False, "error": "Google not connected"}

    access_token = get_valid_access_token(db, user_id)

    settings = dict(token.settings_json or {})
    if sync_settings is None:
        sync_settings = dict(settings.get("sync_settings", DEFAULT_SYNC_SETTINGS))

    task_result = None
    event_result = None

    try:
        task_result = _sync_tasks(db, user_id, access_token, sync_settings)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            body = e.response.text[:200]
            task_result = {"error": f"Tasks API returned 403 — the Google Tasks API may not be enabled in your cloud project. Response: {body}"}
        else:
            task_result = {"error": f"Tasks API HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        task_result = {"error": f"Tasks sync failed: {e}"}

    try:
        event_result = _sync_events(db, user_id, access_token, sync_settings)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            body = e.response.text[:200]
            event_result = {"error": f"Calendar API returned 403 — the Calendar API may not be enabled. Response: {body}"}
        else:
            event_result = {"error": f"Calendar API HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        event_result = {"error": f"Events sync failed: {e}"}

    settings["last_sync_at"] = datetime.utcnow().isoformat()
    settings["sync_settings"] = sync_settings
    token.settings_json = settings
    db.commit()

    logger.info("Google sync complete: tasks=%s events=%s", task_result, event_result)
    return {
        "success": True,
        "tasks": task_result,
        "events": event_result,
        "synced_at": settings["last_sync_at"],
    }
