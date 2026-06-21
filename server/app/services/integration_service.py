import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.integration import IntegrationToken

def encrypt_token(raw_token: str) -> str:
    """
    Mock symmetric encryption for security representations.
    Encodes the raw token in standard base64.
    """
    return base64.b64encode(raw_token.encode("utf-8")).decode("utf-8")

def decrypt_token(enc_token: str) -> str:
    """
    Mock symmetric decryption representation.
    """
    return base64.b64decode(enc_token.encode("utf-8")).decode("utf-8")

def save_integration_config(
    db: Session,
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in_seconds: int = 3600,
    settings: Optional[Dict[str, Any]] = None
) -> IntegrationToken:
    # 1. Encrypt credentials
    enc_access = encrypt_token(access_token)
    enc_refresh = encrypt_token(refresh_token) if refresh_token else None
    
    # 2. Check if integration already exists
    existing = db.query(IntegrationToken).filter(
        IntegrationToken.user_id == user_id,
        IntegrationToken.provider == provider
    ).first()
    
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    
    if existing:
        existing.access_token_enc = enc_access
        existing.refresh_token_enc = enc_refresh
        existing.expires_at = expires_at
        if settings is not None:
            existing.settings_json = settings
        token_entry = existing
    else:
        token_entry = IntegrationToken(
            user_id=user_id,
            provider=provider,
            access_token_enc=enc_access,
            refresh_token_enc=enc_refresh,
            expires_at=expires_at,
            settings_json=settings or {}
        )
        db.add(token_entry)
        
    db.commit()
    db.refresh(token_entry)
    return token_entry

def get_integration_status(db: Session, user_id: int, provider: str) -> Dict[str, Any]:
    token = db.query(IntegrationToken).filter(
        IntegrationToken.user_id == user_id,
        IntegrationToken.provider == provider
    ).first()
    
    if not token:
        return {"connected": False, "provider": provider}
        
    is_expired = datetime.utcnow() > token.expires_at
    return {
        "connected": True,
        "provider": provider,
        "is_expired": is_expired,
        "expires_at": token.expires_at.isoformat(),
        "settings": token.settings_json
    }
