from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Feature, UploadedFile
from app.services.geo_reader import read_geodata
from app.services.measurement import measure_feature


def process_file(db: Session, record: UploadedFile, source_path: Path) -> None:
    """Read the file, measure each feature and save the results."""
    try:
        crs, features = read_geodata(source_path)

        rows = []
        for f in features:
            m = measure_feature(f["geom_object"], crs)
            rows.append(
                Feature(
                    file_id=record.id,
                    feature_index=f["index"],
                    geometry_type=f["geometry_type"],
                    geometry=f["geometry"],
                    properties=f["properties"],
                    area_sq_m=m["area_sq_m"],
                    length_m=m["length_m"],
                    projected_crs=m["projected_crs"],
                    note=m["note"],
                )
            )

        # save everything together, so a file is never half stored
        db.add_all(rows)
        record.crs = crs
        record.feature_count = len(rows)
        record.status = "COMPLETED"
    except Exception as exc:
        db.rollback()
        record = db.get(UploadedFile, record.id)
        record.status = "FAILED"
        # HTTPException keeps its message in .detail
        record.error_message = str(getattr(exc, "detail", exc))

    db.commit()