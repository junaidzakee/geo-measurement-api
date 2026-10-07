# Geospatial File Measurement API

A FastAPI service that accepts a Shapefile (`.zip`) or a KML file, reads the features inside it, and calculates measurements for them.

For polygons it returns **area**, and for lines it returns **length**. Measurements are calculated in metres using a projected CRS, not directly from latitude/longitude degrees.

## Features

- Upload a zipped Shapefile or a KML file
- Read each feature with its properties and geometry (as GeoJSON)
- Area for Polygon and MultiPolygon, length for LineString and MultiLineString
- UTM zone chosen automatically for each feature
- Paginated measurements API
- Status tracking (`PROCESSING`, `COMPLETED`, `FAILED`)
- Basic protection against unsafe ZIP files and oversized uploads
- Docker support
- 16 automated tests

## Tech Stack

- **FastAPI**: API
- **SQLAlchemy + SQLite**: database
- **GeoPandas / Pyogrio**: reading geospatial files
- **Shapely**: geometry operations
- **PyProj**: CRS transformations
- **Pytest**: testing
- **Docker**: containerized setup

## Running Locally

Requires Python 3.10 or newer (Docker uses 3.12).

```bash
git clone https://github.com/junaidzakee/geo-measurement-api.git
cd geo-measurement-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000` and the Swagger docs are at `http://127.0.0.1:8000/docs`.

## Running with Docker

```bash
docker compose up --build
```

The database and uploaded files are stored in `./data`, so they are kept when the container restarts.

## Running Tests

```bash
pytest -v
```

---

# API

## Upload a File

`POST /api/files/` (multipart form, field name `file`)

```bash
curl -F "file=@tests/data/sample.kml" http://127.0.0.1:8000/api/files/
```

```json
{
  "id": "ff765d7325ee",
  "filename": "sample.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null
}
```

Accepted files: `.kml`, or a `.zip` containing a Shapefile (`.shp`, `.shx` and `.dbf` are required).

**Upload errors.** The API returns `400` for an unsupported extension, an invalid ZIP, unsafe ZIP paths, a ZIP with no Shapefile, or a Shapefile missing `.shx` or `.dbf`. Files over the size limit return `413`.

**Processing failures.** If the file is valid but cannot be processed, it is saved with status `FAILED` and a reason. For example, a Shapefile without a `.prj` file:

```json
{
  "id": "f87a86bdb8b2",
  "filename": "noprj.zip",
  "feature_count": 0,
  "crs": null,
  "status": "FAILED",
  "error_message": "File has no CRS information (a shapefile needs a .prj file)"
}
```

I kept these files as `FAILED` instead of rejecting them, so the reason can still be checked through the API.

## Get File Information

`GET /api/files/{id}/` returns the same fields as the upload response. An unknown id returns `404`.

## Get Measurements

`GET /api/files/{id}/measurements/?limit=100&offset=0`

```bash
curl "http://127.0.0.1:8000/api/files/ff765d7325ee/measurements/"
```

Shortened response (the Polygon feature):

```json
{
  "file_id": "ff765d7325ee",
  "status": "COMPLETED",
  "total": 3,
  "limit": 100,
  "offset": 0,
  "features": [
    {
      "index": 0,
      "geometry_type": "Polygon",
      "geometry": { "type": "Polygon", "coordinates": ["..."] },
      "crs": "EPSG:4326",
      "properties": { "Name": "Test Plot" },
      "measurement": {
        "area_sq_m": 1201683.9191,
        "area_hectares": 120.1684,
        "length_m": null,
        "length_km": null,
        "projected_crs": "EPSG:32643",
        "note": null
      }
    }
  ]
}
```

For Point features no measurement is calculated:

```json
{
  "area_sq_m": null,
  "area_hectares": null,
  "length_m": null,
  "length_km": null,
  "projected_crs": null,
  "note": "No measurement for Point"
}
```

If the file status is not `COMPLETED`, this endpoint returns `409` with the reason.

---

# Project Structure

```text
.
├── app/
│   ├── main.py            app creation, router, table creation
│   ├── config.py          paths, size limits, allowed extensions
│   ├── database.py        database engine and session
│   ├── models.py          UploadedFile and Feature tables
│   ├── schemas.py         response models
│   ├── api/
│   │   └── files.py       the three endpoints
│   └── services/
│       ├── file_handler.py   validation, saving, safe ZIP extraction
│       ├── geo_reader.py     reads KML/Shapefile into features
│       ├── measurement.py    CRS handling, area and length
│       └── processor.py      read -> measure -> save for one file
├── tests/
│   ├── conftest.py        temporary database and upload folder per test
│   ├── test_api.py        endpoint tests
│   ├── test_measurement.py   measurement unit tests
│   └── data/              sample KML and Shapefile
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
└── requirements.txt
```

---

# How File Processing Works

1. Check the file extension.
2. Save the upload in 1 MB chunks and stop if it passes the 50 MB limit.
3. For ZIP files: check the declared uncompressed size, check that every path stays inside the target folder, then extract.
4. Find the `.shp` file and confirm `.shx` and `.dbf` exist.
5. Create a database record with status `PROCESSING`.
6. Read the file with GeoPandas and measure each feature.
7. Save all features in one commit and set the status to `COMPLETED`.

If anything fails during steps 5 to 7, the status becomes `FAILED` and the error is stored.

# How Measurements Are Calculated

Area and length are not calculated from EPSG:4326 coordinates, because those are in degrees. For every feature:

1. Convert the geometry to WGS84 and take its centroid.
2. Use the centroid to choose the UTM zone.
3. Transform the original geometry into that UTM zone.
4. Read `.area` or `.length` (in metres).
5. Store the projected CRS used.

Different features in one file can use different UTM zones. `always_xy=True` is used so coordinates are always (longitude, latitude). A file with no CRS is not given a guessed one, because a wrong CRS gives wrong measurements.

---

# Design Decisions

**UTM vs geodesic.** I used UTM because it gives metres and works well for normal-sized features. I checked the sample polygon against a geodesic calculation (`pyproj.Geod`):

```text
UTM area:       1,201,684 m²
Geodesic area:  1,200,290 m²
Difference:     ~0.12%
```

The small difference is expected because the polygon is about 2.6° from the central meridian of its UTM zone, where UTM's scale is slightly above 1. The tests use the geodesic value as a reference.

**SQLite vs PostGIS.** SQLite needs no setup, so the project runs with one command. The trade-off is no spatial indexes or queries. A production version could use PostGIS.

**Synchronous processing.** Processing happens inside the upload request. Uploads are capped at 50 MB, so this is fine for now. The status field is already designed so processing can move to a background worker later.

**FAILED status vs rejecting.** Bad uploads (wrong type, broken ZIP) are rejected immediately. Valid files that cannot be processed are stored as `FAILED` with a reason.

# Security and Validation

- **ZIP slip:** every path is checked before extraction, so names like `../../file` cannot escape the target folder.
- **ZIP bombs:** the declared uncompressed size is checked before extraction. This uses the sizes written in the ZIP headers, so a deliberately faked header could get past it. Extracting with a running byte count would be stricter.
- **Upload size:** the file is read in chunks and stopped at the limit.
- **Filenames:** only the base name is used when saving, never a client-supplied path.

---

# Edge Cases

These are handled in the code:

- Shapefile without a `.prj`
- Missing `.shx` or `.dbf`
- `__MACOSX` junk files inside ZIPs
- Empty geometries
- Invalid geometries (repaired with `make_valid`, and a note is added)
- Unsupported geometry types (null measurements plus a note)
- 3D coordinates from KML (kept in the stored geometry, ignored when measuring)
- `NaN` / `NaT` attribute values (converted to null before saving)
- Invalid ZIPs, unsafe ZIP paths, ZIPs with no Shapefile, oversized files

Covered by automated tests: missing `.prj`, empty geometry, repaired invalid geometry, unsupported type (Point), wrong extension, invalid ZIP, unsafe ZIP path, ZIP without a Shapefile. The others were checked by hand or are not tested yet.

# Tests

16 tests in total.

**Measurement tests (6):** polygon area compared with a geodesic calculation, line length, Point has no measurement, empty geometry, self-intersecting polygon is repaired, UTM zone selection (north and south).

**API tests (10):** KML upload and read back, measurements for a KML, pagination, Shapefile upload, missing `.prj` marked `FAILED` (and measurements return `409`), wrong extension, invalid ZIP, ZIP slip, ZIP without a Shapefile, unknown file id.

Each test uses its own temporary database and upload folder.

---

# Known Limitations

- If a ZIP contains several Shapefiles, only the first one is processed.
- A feature that crosses a UTM zone boundary is measured in the zone of its centre, which adds a small error.
- Processing is synchronous.
- Only the first KML layer is read, so features in other KML folders are skipped. *(delete this line if your two-folder test printed 2)*
- Latitudes outside -80 to 84 are not measured.

# What I Learned

- Why latitude/longitude degrees cannot be used directly for area and length.
- How the choice of CRS changes a measurement, and how to check a result against a geodesic calculation.
- How to pick a UTM zone from a location.
- ZIP slip and ZIP bombs, and how to guard against them.
- `NaN` and `NaT` values from pandas break JSON, so they must be cleaned before saving.
- Keeping the endpoints thin and putting the logic in a services layer made testing easier.

# Future Improvements

- Background processing with Celery and Redis
- PostGIS for spatial storage and queries
- A local equal-area projection for more accurate areas
- Handling features that cross UTM zones, and polar regions (UPS)
- GeoJSON and GeoPackage support
- Reading all KML layers and all Shapefiles inside a ZIP
- Authentication and rate limiting