"""Seed 5 test tasks with sub-blocks into the database."""
import os, datetime

# Force SQLite before any app imports
os.environ["DATABASE_URL"] = "sqlite:///./dopapal_dev.db"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.models.reward import Reward
from app.models.integration import IntegrationToken
from app.core.database import Base

engine = create_engine("sqlite:///./dopapal_dev.db", connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure tables exist
Base.metadata.create_all(engine)
from app.models.user import User
from app.models.task import Task, SubBlock
from app.models.state import StateLog
from app.models.reward import Reward
from app.models.integration import IntegrationToken

SESSIONS = [
    {
        "title": "Build REST API for user auth",
        "source_type": "manual",
        "estimated_hours": 4.0,
        "interest_tag": "architecture",
        "pinch_score": 85.0,
        "sub_blocks": [
            {"title": "Design token-based auth flow", "duration_minutes": 60, "days_from_today": 0},
            {"title": "Implement signup/login endpoints", "duration_minutes": 90, "days_from_today": 0},
            {"title": "Add JWT middleware and guards", "duration_minutes": 45, "days_from_today": 1},
            {"title": "Write integration tests", "duration_minutes": 60, "days_from_today": 1},
        ],
    },
    {
        "title": "Refactor dashboard component structure",
        "source_type": "manual",
        "estimated_hours": 3.0,
        "interest_tag": "architecture",
        "pinch_score": 70.0,
        "sub_blocks": [
            {"title": "Extract reusable card components", "duration_minutes": 45, "days_from_today": 0},
            {"title": "Move state logic to custom hooks", "duration_minutes": 60, "days_from_today": 1},
            {"title": "Update Storybook stories", "duration_minutes": 30, "days_from_today": 2},
        ],
    },
    {
        "title": "Write unit tests for reward service",
        "source_type": "manual",
        "estimated_hours": 2.0,
        "interest_tag": "cybersecurity",
        "pinch_score": 55.0,
        "sub_blocks": [
            {"title": "Test interest vault fact selection", "duration_minutes": 30, "days_from_today": 0},
            {"title": "Test theme unlock logic", "duration_minutes": 30, "days_from_today": 0},
            {"title": "Test completion milestone edge cases", "duration_minutes": 45, "days_from_today": 1},
        ],
    },
    {
        "title": "Deploy staging environment on Fly.io",
        "source_type": "voice",
        "estimated_hours": 1.5,
        "interest_tag": None,
        "pinch_score": 40.0,
        "sub_blocks": [
            {"title": "Configure Dockerfile and fly.toml", "duration_minutes": 30, "days_from_today": 2},
            {"title": "Set up SQLite persistence volume", "duration_minutes": 20, "days_from_today": 2},
            {"title": "Verify health checks pass", "duration_minutes": 15, "days_from_today": 3},
        ],
    },
    {
        "title": "Research WebSocket scaling patterns",
        "source_type": "ai",
        "estimated_hours": 2.5,
        "interest_tag": "architecture",
        "pinch_score": 60.0,
        "sub_blocks": [
            {"title": "Read Redis pub/sub vs NATS comparison", "duration_minutes": 40, "days_from_today": 1},
            {"title": "Prototype horizontal scaling with sticky sessions", "duration_minutes": 60, "days_from_today": 2},
            {"title": "Document findings and recommendations", "duration_minutes": 30, "days_from_today": 3},
        ],
    },
]

def seed():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(
                email="default_user@dopapal.app",
                name="Default User",
                wake_time_pref=datetime.time(7, 30),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created default user (id={user.id})")

        existing = db.query(Task).filter(Task.user_id == user.id).count()
        if existing > 0:
            print(f"User already has {existing} tasks. Skipping seed.")
            return

        today = datetime.date.today()
        for i, spec in enumerate(SESSIONS):
            task = Task(
                user_id=user.id,
                title=spec["title"],
                source_type=spec["source_type"],
                deadline=datetime.datetime.now() + datetime.timedelta(days=i + 1),
                estimated_hours=spec["estimated_hours"],
                interest_tag=spec["interest_tag"],
                pinch_score=spec["pinch_score"],
            )
            db.add(task)
            db.flush()

            for seq, sb in enumerate(spec["sub_blocks"], start=1):
                db.add(SubBlock(
                    task_id=task.id,
                    sequence=seq,
                    title=sb["title"],
                    duration_minutes=sb["duration_minutes"],
                    scheduled_date=today + datetime.timedelta(days=sb["days_from_today"]),
                ))

        db.commit()
        print(f"Seeded 5 tasks ({sum(len(s['sub_blocks']) for s in SESSIONS)} sub-blocks) for user {user.id}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
