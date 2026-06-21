import os
from app.core.database import engine, Base
from app.models.user import User
from app.models.task import Task
from app.models.state import StateLog

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Database reset complete.")
