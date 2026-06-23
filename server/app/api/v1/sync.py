import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.tasks import get_or_create_default_user
from app.core.database import get_db
from app.services.google_service import sync_google, get_token_entry
from app.services.constants import DEFAULT_SYNC_SETTINGS
from app.services.integration_service import get_integration_status

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
        token = get_token_entry(db, user.id)
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
    token = get_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_SYNC_SETTINGS)
    stored = (token.settings_json or {}).get("sync_settings", {})
    merged = {**DEFAULT_SYNC_SETTINGS, **stored}
    return SyncSettingsResponse(settings=merged)


@router.put("/sync/google/settings", response_model=SyncSettingsResponse)
def update_google_sync_settings(body: SyncSettingsUpdate, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    token = get_token_entry(db, user.id)
    if not token:
        return SyncSettingsResponse(settings=DEFAULT_SYNC_SETTINGS)
    settings = dict(token.settings_json or {})
    settings["sync_settings"] = body.settings
    token.settings_json = settings
    db.commit()
    merged = {**DEFAULT_SYNC_SETTINGS, **body.settings}
    return SyncSettingsResponse(settings=merged)
