from app.models.user import User
from app.models.task import Task
from app.models.state import StateLog
from app.core.database import SessionLocal

db = SessionLocal()
try:
    deleted_tasks = db.query(Task).delete()
    deleted_users = db.query(User).delete()
    db.commit()
    print(f"Deleted {deleted_tasks} tasks and {deleted_users} users.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
