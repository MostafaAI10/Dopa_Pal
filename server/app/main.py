import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal

# Import models to register them with SQLAlchemy Base
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.models.reward import Reward
from app.models.integration import IntegrationToken

# Import routers
from app.api.v1.tasks import router as tasks_router
from app.api.v1.state import router as state_router
from app.api.v1.users import router as users_router
from app.api.v1.rewards import router as rewards_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.chat import router as chat_router
from app.api.v1.auth_google import router as auth_google_router
from app.api.v1.sync import router as sync_router

from app.services.websocket_manager import manager as ws_manager
from app.services.google_service import sync_google, get_token_entry, SYNC_INTERVAL_MINUTES

logger = logging.getLogger(__name__)


_background_tasks: list[asyncio.Task] = []
_sync_event = asyncio.Event()


async def _periodic_google_sync():
    """Run Google sync every SYNC_INTERVAL_MINUTES for each connected user."""
    while not _sync_event.is_set():
        try:
            db = SessionLocal()
            try:
                tokens = db.query(IntegrationToken).filter(
                    IntegrationToken.provider == "google"
                ).all()
                for token in tokens:
                    try:
                        sync_google(db, token.user_id)
                        logger.info("Background sync completed for user %d", token.user_id)
                    except Exception as e:
                        logger.warning("Background sync failed for user %d: %s", token.user_id, e)
            finally:
                db.close()
        except Exception as e:
            logger.error("Background sync loop error: %s", e)

        try:
            await asyncio.wait_for(
                _sync_event.wait(),
                timeout=SYNC_INTERVAL_MINUTES * 60,
            )
            break  # _sync_event was set → shut down
        except asyncio.TimeoutError:
            continue  # timeout elapsed → run sync again


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await ws_manager.startup()

    task = asyncio.create_task(_periodic_google_sync())
    _background_tasks.append(task)

    yield

    _sync_event.set()
    for t in _background_tasks:
        t.cancel()
    await ws_manager.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="The Ambient Cognitive Translation Layer for the ADHD Brain",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for local client development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(tasks_router, prefix=settings.API_V1_STR)
app.include_router(state_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(rewards_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(auth_google_router, prefix=settings.API_V1_STR)
app.include_router(sync_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "docs_url": "/docs",
        "version": "0.1.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
