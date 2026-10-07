from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app import models
from app.api import files
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

tags_metadata = [
    {
        "name": "files",
        "description": "Upload a geospatial file, then read back its details and measurements.",
    },
    {
        "name": "system",
        "description": "Basic check that the service is running.",
    },
]

app = FastAPI(
    title="Geospatial File Measurement API",
    version="1.0.0",
    description=(
        "Upload a KML file or a zipped Shapefile and get back the area of each polygon "
        "and the length of each line, in metres.\n\n"
        "**How to use it:**\n"
        "1. Upload a file with `POST /api/files/` and copy the `id` from the response "
        "(copy only the letters and numbers, without the quotes).\n"
        "2. Check the file with `GET /api/files/{file_id}/`.\n"
        "3. Get the measurements with `GET /api/files/{file_id}/measurements/`.\n\n"
        "Measurements are calculated in a UTM projection, never in degrees."
    ),
    openapi_tags=tags_metadata,
)

app.include_router(files.router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=tags_metadata,
    )
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            operation.get("responses", {}).pop("422", None)
    schemas = schema.get("components", {}).get("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/health", tags=["system"], summary="Check that the service is running")
def health():
    return {"status": "ok"}