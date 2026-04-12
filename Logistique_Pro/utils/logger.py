from datetime import datetime
from pathlib import Path

LOG_FILE = Path("data/app.log")

def log_action(action: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {action}\n")
