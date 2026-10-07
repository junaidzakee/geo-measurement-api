from pydantic import BaseModel, ConfigDict


class FileInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    feature_count: int
    crs: str | None = None
    status: str
    error_message: str | None = None


class Measurement(BaseModel):
    area_sq_m: float | None = None
    area_hectares: float | None = None
    length_m: float | None = None
    length_km: float | None = None
    projected_crs: str | None = None
    note: str | None = None


class FeatureOut(BaseModel):
    index: int
    geometry_type: str | None = None
    geometry: dict | None = None
    crs: str | None = None
    properties: dict | None = None
    measurement: Measurement


class MeasurementsResponse(BaseModel):
    file_id: str
    status: str
    total: int
    limit: int
    offset: int
    features: list[FeatureOut]