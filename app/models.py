import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def new_id():
    return uuid.uuid4().hex[:12]


def now_utc():
    return datetime.now(timezone.utc)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=new_id)
    filename = Column(String, nullable=False)
    status = Column(String, default="PROCESSING")  # PROCESSING, COMPLETED or FAILED
    crs = Column(String, nullable=True)
    feature_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    features = relationship(
        "Feature", back_populates="file", cascade="all, delete-orphan"
    )


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("uploaded_files.id"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    geometry_type = Column(String, nullable=True)
    geometry = Column(JSON, nullable=True)      # stored as GeoJSON
    properties = Column(JSON, nullable=True)
    area_sq_m = Column(Float, nullable=True)
    length_m = Column(Float, nullable=True)
    projected_crs = Column(String, nullable=True)  # CRS used for the measurement
    note = Column(String, nullable=True)           # e.g. "not applicable for Point"

    file = relationship("UploadedFile", back_populates="features")