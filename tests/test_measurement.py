import pytest
from pyproj import Geod
from shapely.geometry import LineString, Point, Polygon

from app.services.measurement import measure_feature, pick_utm_crs

SQUARE = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98)])


def test_polygon_area_matches_geodesic():
    result = measure_feature(SQUARE, "EPSG:4326")
    geodesic_area = abs(Geod(ellps="WGS84").geometry_area_perimeter(SQUARE)[0])
    assert result["area_sq_m"] == pytest.approx(geodesic_area, rel=0.002)
    assert result["projected_crs"] == "EPSG:32643"


def test_line_length_in_metres():
    line = LineString([(77.59, 12.97), (77.60, 12.98)])
    result = measure_feature(line, "EPSG:4326")
    assert result["length_m"] == pytest.approx(1550, rel=0.01)


def test_point_has_no_measurement():
    result = measure_feature(Point(77.59, 12.97), "EPSG:4326")
    assert result["area_sq_m"] is None
    assert result["length_m"] is None
    assert "No measurement" in result["note"]


def test_empty_geometry_does_not_crash():
    result = measure_feature(None, "EPSG:4326")
    assert result["note"] is not None


def test_self_intersecting_polygon_is_repaired():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    result = measure_feature(bowtie, "EPSG:4326")
    assert result["area_sq_m"] is not None
    assert "repaired" in result["note"]


def test_utm_zone_selection():
    assert pick_utm_crs(77.6, 12.9).to_epsg() == 32643
    assert pick_utm_crs(151.2, -33.9).to_epsg() == 32756
