from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base

# Import models to register them with SQLAlchemy Base
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.models.reward import Reward
from app.models.integration import IntegrationToken

# Import routers
from app.api.v1.tasks import router as tasks_router
from app.api.v1.state import router as state_router
from app.api.v1.rewards import router as rewards_router
from app.api.v1.integrations import router as integrations_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create database tables if they do not exist
    # This acts as an automated migration for local compose setups
    Base.metadata.create_all(bind=engine)
    yield

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
app.include_router(rewards_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)

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
