from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.core.database import get_db
from app.services import integration_service
from app.api.v1.tasks import get_or_create_default_user

router = APIRouter()

# Schemas
class IntegrationConfigRequest(BaseModel):
    provider: str = Field(..., description="Provider, e.g. 'google', 'notion', 'jira', 'canvas'")
    access_token: str = Field(..., description="API Key or OAuth access token")
    refresh_token: Optional[str] = None
    expires_in_seconds: int = 3600
    settings: Optional[Dict[str, Any]] = None

class IntegrationStatusResponse(BaseModel):
    connected: bool
    provider: str
    is_expired: Optional[bool] = None
    expires_at: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

@router.post("/integrations/config", response_model=IntegrationStatusResponse)
def configure_integration(payload: IntegrationConfigRequest, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    
    # Save/update configuration
    token_entry = integration_service.save_integration_config(
        db=db,
        user_id=user.id,
        provider=payload.provider.lower(),
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        expires_in_seconds=payload.expires_in_seconds,
        settings=payload.settings
    )
    
    # Return connections status
    status = integration_service.get_integration_status(db, user.id, payload.provider.lower())
    return status

@router.delete("/integrations/config/{provider}")
def delete_integration(provider: str, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    deleted = integration_service.delete_integration_config(db, user.id, provider.lower())
    if not deleted:
        raise HTTPException(status_code=404, detail=f"{provider} not connected")
    return {"success": True, "provider": provider}

@router.get("/integrations/status/{provider}", response_model=IntegrationStatusResponse)
def get_single_integration_status(provider: str, db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    status = integration_service.get_integration_status(db, user.id, provider.lower())
    return status

@router.get("/integrations/status", response_model=List[IntegrationStatusResponse])
def get_all_integrations_status(db: Session = Depends(get_db)):
    user = get_or_create_default_user(db)
    providers = ["google", "notion", "jira", "canvas"]
    statuses = []
    for p in providers:
        status = integration_service.get_integration_status(db, user.id, p)
        statuses.append(status)
    return statuses
