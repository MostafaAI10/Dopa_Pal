from pathlib import Path
import sys


SERVER_ROOT = Path(__file__).resolve().parents[2]

if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
