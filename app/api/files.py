import shutil

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import get_db
from app.models import Feature, UploadedFile, new_id
from app.schemas import FeatureOut, FileInfo, Measurement, MeasurementsResponse
from app.services import file_handler
from app.services.processor import process_file

router = APIRouter(prefix="/api/files", tags=["files"])

FILE_ID_HELP = "File id from the upload response, without quotes"


def get_file_or_404(db: Session, file_id: str) -> UploadedFile:
    record = db.get(UploadedFile, file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@router.post(
    "/",
    response_model=FileInfo,
    status_code=201,
    summary="Upload a KML or zipped Shapefile",
    description=(
        "Send a `.kml` file or a `.zip` containing a Shapefile. The file is read and every "
        "feature is measured. The response shows the file `id` and its `status`.\n\n"
        "If the file is valid but cannot be processed (for example a Shapefile with no `.prj`), "
        "it is saved with status `FAILED` and an `error_message`."
    ),
)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = file_handler.check_extension(file.filename or "")
    file_id = new_id()

    try:
        saved_path = file_handler.save_upload(file, file_id)
        if ext == ".zip":
            extracted = file_handler.extract_zip(saved_path)
            source_path = file_handler.find_shapefile(extracted)
        else:
            source_path = saved_path
    except HTTPException:
        shutil.rmtree(UPLOAD_DIR / file_id, ignore_errors=True)
        raise

    record = UploadedFile(id=file_id, filename=file.filename)
    db.add(record)
    db.commit()

    process_file(db, record, source_path)
    db.refresh(record)
    return record


@router.get(
    "/{file_id}/",
    response_model=FileInfo,
    summary="Get details of an uploaded file",
    description="Returns the filename, CRS, number of features and processing status.",
)
def get_file(
    file_id: str = Path(description=FILE_ID_HELP),
    db: Session = Depends(get_db),
):
    return get_file_or_404(db, file_id)


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get area and length for each feature",
    description=(
        "Polygons get an area, lines get a length, and points have no measurement. "
        "Use `limit` and `offset` to page through large files."
    ),
)
def get_measurements(
    file_id: str = Path(description=FILE_ID_HELP),
    limit: int = Query(100, ge=1, le=1000, description="How many features to return"),
    offset: int = Query(0, ge=0, description="How many features to skip"),
    db: Session = Depends(get_db),
):
    record = get_file_or_404(db, file_id)

    if record.status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=f"File status is {record.status}. {record.error_message or ''}".strip(),
        )

    rows = (
        db.query(Feature)
        .filter(Feature.file_id == file_id)
        .order_by(Feature.feature_index)
        .offset(offset)
        .limit(limit)
        .all()
    )

    features = []
    for r in rows:
        features.append(
            FeatureOut(
                index=r.feature_index,
                geometry_type=r.geometry_type,
                geometry=r.geometry,
                crs=record.crs,
                properties=r.properties,
                measurement=Measurement(
                    area_sq_m=_round(r.area_sq_m),
                    area_hectares=_round(r.area_sq_m / 10_000) if r.area_sq_m is not None else None,
                    length_m=_round(r.length_m),
                    length_km=_round(r.length_m / 1000) if r.length_m is not None else None,
                    projected_crs=r.projected_crs,
                    note=r.note,
                ),
            )
        )

    return MeasurementsResponse(
        file_id=record.id,
        status=record.status,
        total=record.feature_count,
        limit=limit,
        offset=offset,
        features=features,
    )


def _round(value):
    return round(value, 4) if value is not None else None