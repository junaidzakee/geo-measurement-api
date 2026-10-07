import json

import geopandas as gpd
import pandas as pd
from fastapi import HTTPException
from shapely.geometry import mapping


def read_geodata(path):
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not read geospatial data: {exc}"
        )

    if gdf.crs is None:
        raise HTTPException(
            status_code=422,
            detail="File has no CRS information (a shapefile needs a .prj file)",
        )

    crs = gdf.crs.to_string()

    features = []
    for index, row in gdf.iterrows():
        geom = row.geometry

        properties = {
            key: _clean_value(value)
            for key, value in row.items()
            if key != "geometry"
        }
        properties = {k: v for k, v in properties.items() if v is not None}

        if geom is None or geom.is_empty:
            features.append(
                {
                    "index": int(index),
                    "geometry_type": None,
                    "geometry": None,
                    "properties": properties,
                    "geom_object": None,
                }
            )
            continue

        features.append(
            {
                "index": int(index),
                "geometry_type": geom.geom_type,
                "geometry": mapping(geom),
                "properties": properties,
                "geom_object": geom,
            }
        )

    return crs, features


def _clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        value = value.item()
    return json.loads(json.dumps(value, default=str))