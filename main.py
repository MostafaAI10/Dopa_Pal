import uvicorn
import sys
import os

def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
    sys.path.insert(0, server_dir)
    os.environ["PYTHONPATH"] = server_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
    
    print("🧠 Starting dopaPal FastAPI Server locally via uvicorn...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=server_dir)

if __name__ == "__main__":
    main()
