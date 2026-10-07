from fastapi import FastAPI

from app import models  # noqa: F401
from app.api import files
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Geospatial File Measurement API")
app.include_router(files.router)


@app.get("/health")
def health():
    return {"status": "ok"}