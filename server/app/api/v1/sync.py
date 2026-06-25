import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.tasks import get_or_create_default_user
from app.core.database import get_db
from app.services.google_service import sync_google, get_token_entry as google_token_entry
from app.services.constants import DEFAULT_SYNC_SETTINGS
from app.services.integration_service import get_integration_status
from app.services.notion_service import (
    sync_notion,
    get_token_entry as notion_token_entry,
    DEFAULT_NOTION_SETTINGS,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sync"])


class SyncResponse(BaseModel):
    success: bool
    tasks: dict | None = None
    events: dict | None = None
    synced_at: str | None = None
    error: str | None = None


class SyncStatusResponse(BaseModel):
    connected: bool
    is_expired: bool = False
    expires_at: str | None = None
    last_synced_at: str | None = None


class SyncSettingsResponse(BaseModel):
    settings: Dict[str, Any]


class SyncSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


class NotionSyncResponse(BaseModel):
    success: bool
    pages_fetched: int = 0
    new: int = 0
    skipped_duplicate: int = 0
    skipped_completed: int = 0
    skipped_no_title: int = 0
    failed: int = 0
    synced_at: str | None = None
    error: str | None = None



@router.post("/sync/google", response_model=SyncResponse)
def trigger_google_sync(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    result = sync_google(db, user.id)
    return SyncResponse(**result)


@router.get("/sync/google/status", response_model=SyncStatusResponse)
def google_sync_status(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    status = get_integration_status(db, user.id, "google")
    last_synced = None
    if status.get("connected"):
        token = google_token_entry(db, user.id)
        if token and token.settings_json:
            last_synced = token.settings_json.get("last_sync_at")
    return SyncStatusResponse(
        connected=status.get("connected", False),
        is_expired=status.get("is_expired", False),
        expires_at=status.get("expires_at"),
        last_synced_at=last_synced,
    )


@router.get("/sync/google/settings", response_model=SyncSettingsResponse)
def get_google_sync_settings(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    token = google_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_SYNC_SETTINGS)
    stored = (token.settings_json or {}).get("sync_settings", {})
    merged = {**DEFAULT_SYNC_SETTINGS, **stored}
    return SyncSettingsResponse(settings=merged)


@router.put("/sync/google/settings", response_model=SyncSettingsResponse)
def update_google_sync_settings(body: SyncSettingsUpdate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    token = google_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_SYNC_SETTINGS)
    settings = dict(token.settings_json or {})
    settings["sync_settings"] = body.settings
    token.settings_json = settings
    db.commit()
    merged = {**DEFAULT_SYNC_SETTINGS, **body.settings}
    return SyncSettingsResponse(settings=merged)


class NotionDatabasesResponse(BaseModel):
    databases: list[dict[str, str]]


class NotionDatabaseSchemaResponse(BaseModel):
    properties: list[dict[str, Any]]


# ── Notion sync endpoints ────────────────────────────────────────────────


@router.get("/sync/notion/databases", response_model=NotionDatabasesResponse)
async def list_notion_databases(db: Session = Depends(get_db)):
    """Return all databases the connected Notion integration can access."""
    user = get_or_create_default_user(db)
    try:
        from app.services.notion_service import (
            validate_notion_token,
            fetch_accessible_databases,
            _db_title,
        )
        token = validate_notion_token(db, user.id)
        raw = await fetch_accessible_databases(token)
        databases = [
            {"id": d["id"], "title": _db_title(d)}
            for d in raw
        ]
        return NotionDatabasesResponse(databases=databases)
    except RuntimeError as e:
        return NotionDatabasesResponse(databases=[])
    except Exception as e:
        logger.warning("Failed to list Notion databases: %s", e)
        return NotionDatabasesResponse(databases=[])


@router.get("/sync/notion/database-schema", response_model=NotionDatabaseSchemaResponse)
async def get_notion_database_schema(
    database_id: str,
    db: Session = Depends(get_db),
):
    """Return the property schema for a given Notion database.

    Each property includes ``name``, ``type``, and type-specific ``options``
    (e.g. ``select.options``, ``status.options``).
    """
    user = get_or_create_default_user(db)
    try:
        from app.services.notion_service import (
            validate_notion_token,
            fetch_database_schema,
        )
        token = validate_notion_token(db, user.id)
        raw = await fetch_database_schema(token, database_id)
        props_raw = raw.get("properties", {})
        properties = []
        for name, prop in props_raw.items():
            if not isinstance(prop, dict):
                continue
            entry: dict[str, Any] = {"name": name, "type": prop.get("type", "")}
            ptype = entry["type"]
            inner = prop.get(ptype)
            if isinstance(inner, dict) and "options" in inner:
                entry["options"] = inner["options"]
            properties.append(entry)
        return NotionDatabaseSchemaResponse(properties=properties)
    except RuntimeError:
        return NotionDatabaseSchemaResponse(properties=[])
    except Exception as e:
        logger.warning("Failed to fetch Notion database schema: %s", e)
        return NotionDatabaseSchemaResponse(properties=[])


@router.post("/sync/notion", response_model=NotionSyncResponse)
async def trigger_notion_sync(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    result = await sync_notion(db, user.id)
    return NotionSyncResponse(**result)


@router.get("/sync/notion/status", response_model=SyncStatusResponse)
def notion_sync_status(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    status = get_integration_status(db, user.id, "notion")
    last_synced = None
    if status.get("connected"):
        token = notion_token_entry(db, user.id)
        if token and token.settings_json:
            last_synced = token.settings_json.get("last_synced_at")
    return SyncStatusResponse(
        connected=status.get("connected", False),
        is_expired=status.get("is_expired", False),
        expires_at=status.get("expires_at"),
        last_synced_at=last_synced,
    )


@router.get("/sync/notion/settings", response_model=SyncSettingsResponse)
def get_notion_sync_settings(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    token = notion_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_NOTION_SETTINGS)
    stored = token.settings_json or {}
    merged: dict[str, Any] = {}
    for k in DEFAULT_NOTION_SETTINGS:
        merged[k] = stored.get(k, DEFAULT_NOTION_SETTINGS[k])
        if isinstance(DEFAULT_NOTION_SETTINGS[k], dict) and isinstance(stored.get(k), dict):
            merged[k] = {**DEFAULT_NOTION_SETTINGS[k], **stored[k]}
    return SyncSettingsResponse(settings=merged)


@router.put("/sync/notion/settings", response_model=SyncSettingsResponse)
def update_notion_sync_settings(body: SyncSettingsUpdate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    token = notion_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_NOTION_SETTINGS)
    settings = dict(token.settings_json or {})
    for k, v in body.settings.items():
        if isinstance(v, dict) and isinstance(settings.get(k), dict):
            settings[k] = {**settings[k], **v}
        else:
            settings[k] = v
    token.settings_json = settings
    db.commit()
    return SyncSettingsResponse(settings=settings)
