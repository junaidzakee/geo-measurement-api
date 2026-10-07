import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import get_db
from app.models import UploadedFile, new_id
from app.schemas import FileInfo
from app.services import file_handler

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/", response_model=FileInfo, status_code=201)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = file_handler.check_extension(file.filename or "")
    file_id = new_id()

    try:
        saved_path = file_handler.save_upload(file, file_id)
        if ext == ".zip":
            extracted = file_handler.extract_zip(saved_path)
            file_handler.find_shapefile(extracted)
    except HTTPException:
        # don't leave half-saved files behind
        shutil.rmtree(UPLOAD_DIR / file_id, ignore_errors=True)
        raise

    record = UploadedFile(id=file_id, filename=file.filename)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record