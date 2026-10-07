import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# in Docker this points at a mounted folder, locally it defaults to the project root
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR))
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'geo_api.db'}"

MAX_UPLOAD_MB = 50
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".zip", ".kml"}

UPLOAD_DIR.mkdir(exist_ok=True)

MAX_UNZIPPED_MB = 200
MAX_UNZIPPED_BYTES = MAX_UNZIPPED_MB * 1024 * 1024