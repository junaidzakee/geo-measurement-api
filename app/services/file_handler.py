import shutil
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import (
    ALLOWED_EXTENSIONS,
    MAX_UNZIPPED_BYTES,
    MAX_UPLOAD_BYTES,
    UPLOAD_DIR,
)


def check_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .zip (shapefile) and .kml files are supported",
        )
    return ext


def save_upload(upload: UploadFile, file_id: str) -> Path:
    folder = UPLOAD_DIR / file_id
    folder.mkdir(parents=True, exist_ok=True)

    dest = folder / Path(upload.filename).name

    size = 0
    try:
        with open(dest, "wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File is too large")
                out.write(chunk)
    except HTTPException:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    if size == 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return dest


def extract_zip(zip_path: Path) -> Path:
    target = zip_path.parent / "extracted"
    target.mkdir(exist_ok=True)
    target_root = target.resolve()

    try:
        with zipfile.ZipFile(zip_path) as zf:
            members = zf.infolist()

            if sum(m.file_size for m in members) > MAX_UNZIPPED_BYTES:
                raise HTTPException(status_code=413, detail="Zip is too large when extracted")

            for m in members:
                if not (target / m.filename).resolve().is_relative_to(target_root):
                    raise HTTPException(status_code=400, detail="Zip contains an unsafe path")

            zf.extractall(target)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid zip archive")

    return target


def find_shapefile(folder: Path) -> Path:
    shp_files = sorted(
        p
        for p in folder.rglob("*.shp")
        if "__MACOSX" not in p.parts and not p.name.startswith("._")
    )
    if not shp_files:
        raise HTTPException(status_code=400, detail="No .shp file found inside the zip")

    shp = shp_files[0]
    names = {p.name.lower() for p in shp.parent.iterdir()}
    for ext in (".shx", ".dbf"):
        if shp.stem.lower() + ext not in names:
            raise HTTPException(
                status_code=400,
                detail=f"Shapefile is incomplete, missing {ext} file",
            )
    return shp