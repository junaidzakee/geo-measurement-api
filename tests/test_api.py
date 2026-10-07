import shutil
import zipfile
from pathlib import Path

DATA = Path(__file__).parent / "data"


def upload(client, path, filename=None):
    with open(path, "rb") as f:
        return client.post(
            "/api/files/", files={"file": (filename or Path(path).name, f)}
        )


def test_upload_kml_and_read_back(client):
    resp = upload(client, DATA / "sample.kml")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["feature_count"] == 3
    assert body["crs"] == "EPSG:4326"

    info = client.get(f"/api/files/{body['id']}/")
    assert info.status_code == 200
    assert info.json()["filename"] == "sample.kml"


def test_measurements_for_kml(client):
    file_id = upload(client, DATA / "sample.kml").json()["id"]
    data = client.get(f"/api/files/{file_id}/measurements/").json()

    by_type = {f["geometry_type"]: f for f in data["features"]}
    assert by_type["Polygon"]["measurement"]["area_sq_m"] > 1_000_000
    assert by_type["LineString"]["measurement"]["length_m"] > 1_000
    assert by_type["Point"]["measurement"]["area_sq_m"] is None


def test_pagination(client):
    file_id = upload(client, DATA / "sample.kml").json()["id"]
    data = client.get(f"/api/files/{file_id}/measurements/?limit=1&offset=1").json()
    assert data["total"] == 3
    assert len(data["features"]) == 1
    assert data["features"][0]["index"] == 1


def test_upload_shapefile_zip(client):
    resp = upload(client, DATA / "sample_shp.zip")
    assert resp.status_code == 201
    assert resp.json()["status"] == "COMPLETED"
    assert resp.json()["feature_count"] == 1


def test_shapefile_without_prj_is_marked_failed(client, tmp_path):
    src = DATA / "sample_shp.zip"
    out = tmp_path / "noprj.zip"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            if not item.filename.endswith(".prj"):
                zout.writestr(item, zin.read(item.filename))

    resp = upload(client, out)
    assert resp.status_code == 201
    assert resp.json()["status"] == "FAILED"
    assert "CRS" in resp.json()["error_message"]

    # measurements are not available for a failed file
    file_id = resp.json()["id"]
    assert client.get(f"/api/files/{file_id}/measurements/").status_code == 409


def test_wrong_extension_rejected(client, tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    assert upload(client, txt).status_code == 400


def test_invalid_zip_rejected(client, tmp_path):
    fake = tmp_path / "fake.zip"
    fake.write_text("not a zip")
    assert upload(client, fake).status_code == 400


def test_zip_slip_rejected(client, tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../escape.txt", "bad")
    resp = upload(client, evil)
    assert resp.status_code == 400
    assert "unsafe" in resp.json()["detail"]


def test_zip_without_shp_rejected(client, tmp_path):
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("readme.txt", "no shapefile here")
    assert upload(client, empty).status_code == 400


def test_unknown_file_id_returns_404(client):
    assert client.get("/api/files/doesnotexist/").status_code == 404