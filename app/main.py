from fastapi import FastAPI

from app import models  # noqa: F401  (needed so the tables get registered)
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Geospatial File Measurement API")


@app.get("/health")
def health():
    return {"status": "ok"}