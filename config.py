import os

def _load_dotenv():
    path = ".env"
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

def get_room_id():
    _load_dotenv()
    rid = os.environ.get("ROOM_ID")
    if not rid:
        try:
            rid = input("ROOM_ID: ").strip()
        except Exception:
            rid = None
        if not rid:
            raise RuntimeError("ROOM_ID env var required")
        os.environ["ROOM_ID"] = rid
    return rid

def get_api_key():
    _load_dotenv()
    key = os.environ.get("API_KEY")
    if not key:
        try:
            key = input("API_KEY: ").strip()
        except Exception:
            key = None
        if not key:
            raise RuntimeError("API_KEY env var required")
        os.environ["API_KEY"] = key
    return key