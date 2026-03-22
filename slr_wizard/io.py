# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# Proprietary Software -- Internal Use Only
# Protected under US and International copyright, trade secret,
# trademark, cybersecurity, and intellectual property law.
# This Product is developed under CVG's Agentic Development Framework (ADF).
# Unauthorized use, replication, or modification is strictly prohibited.
# -----------------------------------------------------------------------------
# Author      : Alex Zelenski, GISP
# Organization: Clearview Geographic, LLC
# Contact     : azelenski@clearviewgeographic.com  |  386-957-2314
# License     : Proprietary -- CVG-ADF
# =============================================================================
"""
io.py — Raster and vector I/O utilities for the SLR Wizard.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.warp import calculate_default_transform, reproject
    from rasterio.mask import mask as rio_mask
    _RASTERIO_OK = True
except ImportError:
    _RASTERIO_OK = False
    log.warning("rasterio not available — raster I/O will be limited.")

try:
    import fiona
    from fiona.crs import from_epsg
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union
    _FIONA_OK = True
except ImportError:
    _FIONA_OK = False
    log.warning("fiona/shapely not available — vector I/O will be limited.")


# ---------------------------------------------------------------------------
# RasterData container
# ---------------------------------------------------------------------------

@dataclass
class RasterData:
    """Holds a numpy array plus metadata from a rasterio read."""
    data: np.ndarray
    transform: Any          # rasterio Affine
    crs: Any                # rasterio CRS
    nodata: float
    width: int
    height: int
    dtype: str = "float32"

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.height, self.width)

    @property
    def resolution_m(self) -> Tuple[float, float]:
        """Return (x_res, y_res) in native units."""
        if self.transform is None:
            return (0.0, 0.0)
        return (abs(self.transform.a), abs(self.transform.e))

    def masked_array(self) -> np.ma.MaskedArray:
        return np.ma.masked_equal(self.data.copy(), self.nodata)

    def stats(self) -> Dict[str, float]:
        arr = self.masked_array()
        if arr.count() == 0:
            return {"min": None, "max": None, "mean": None, "std": None}
        return {
            "min": float(arr.min()),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "std": float(arr.std()),
        }


# ---------------------------------------------------------------------------
# Read / Write
# ---------------------------------------------------------------------------

def read_raster(path: str | Path) -> RasterData:
    """Read a single-band raster into a :class:`RasterData` object."""
    if not _RASTERIO_OK:
        raise ImportError("rasterio is required for raster I/O.")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Raster not found: {p}")
    with rasterio.open(p) as src:
        data = src.read(1).astype("float32")
        nodata = src.nodata if src.nodata is not None else -9999.0
        return RasterData(
            data=data,
            transform=src.transform,
            crs=src.crs,
            nodata=float(nodata),
            width=src.width,
            height=src.height,
            dtype="float32",
        )


def write_raster(
    raster: RasterData,
    path: str | Path,
    compress: bool = True,
) -> None:
    """Write a :class:`RasterData` to a GeoTIFF."""
    if not _RASTERIO_OK:
        raise ImportError("rasterio is required for raster I/O.")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    profile: Dict[str, Any] = {
        "driver": "GTiff",
        "dtype": raster.dtype,
        "width": raster.width,
        "height": raster.height,
        "count": 1,
        "crs": raster.crs,
        "transform": raster.transform,
        "nodata": raster.nodata,
    }
    if compress:
        profile["compress"] = "lzw"
        profile["tiled"] = True
        profile["blockxsize"] = 256
        profile["blockysize"] = 256
    with rasterio.open(p, "w", **profile) as dst:
        dst.write(raster.data.astype(raster.dtype), 1)
    log.info("Raster written → %s", p)


def reproject_to_match(source: RasterData, target: RasterData) -> RasterData:
    """Reproject and resample *source* to match the grid of *target*."""
    if not _RASTERIO_OK:
        raise ImportError("rasterio is required.")
    dst_data = np.full((target.height, target.width), source.nodata, dtype="float32")
    reproject(
        source=source.data,
        destination=dst_data,
        src_transform=source.transform,
        src_crs=source.crs,
        src_nodata=source.nodata,
        dst_transform=target.transform,
        dst_crs=target.crs,
        dst_nodata=source.nodata,
        resampling=Resampling.bilinear,
    )
    return RasterData(
        data=dst_data,
        transform=target.transform,
        crs=target.crs,
        nodata=source.nodata,
        width=target.width,
        height=target.height,
    )


def reproject_raster(
    raster: RasterData,
    target_crs: str,
) -> RasterData:
    """Reproject *raster* to *target_crs* (e.g. 'EPSG:4326')."""
    if not _RASTERIO_OK:
        raise ImportError("rasterio is required.")
    dst_crs = CRS.from_string(target_crs)
    transform, width, height = calculate_default_transform(
        raster.crs, dst_crs, raster.width, raster.height, transform=raster.transform
    )
    dst_data = np.full((height, width), raster.nodata, dtype="float32")
    reproject(
        source=raster.data,
        destination=dst_data,
        src_transform=raster.transform,
        src_crs=raster.crs,
        src_nodata=raster.nodata,
        dst_transform=transform,
        dst_crs=dst_crs,
        dst_nodata=raster.nodata,
        resampling=Resampling.bilinear,
    )
    return RasterData(
        data=dst_data,
        transform=transform,
        crs=dst_crs,
        nodata=raster.nodata,
        width=width,
        height=height,
    )


def clip_to_aoi(raster: RasterData, aoi_path: str | Path) -> RasterData:
    """Clip *raster* to the AOI defined by a vector file."""
    if not _RASTERIO_OK or not _FIONA_OK:
        raise ImportError("rasterio and fiona are required for clip_to_aoi.")
    p = Path(aoi_path)
    with fiona.open(p, "r") as src:
        shapes = [feature["geometry"] for feature in src]
    # Write to temp in-memory rasterio dataset
    import io
    import rasterio.io as rio_io
    memfile = rio_io.MemoryFile()
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": raster.width,
        "height": raster.height,
        "count": 1,
        "crs": raster.crs,
        "transform": raster.transform,
        "nodata": raster.nodata,
    }
    with memfile.open(**profile) as dataset:
        dataset.write(raster.data, 1)
        clipped, clipped_transform = rio_mask(dataset, shapes, crop=True, nodata=raster.nodata)
    data = clipped[0].astype("float32")
    return RasterData(
        data=data,
        transform=clipped_transform,
        crs=raster.crs,
        nodata=raster.nodata,
        width=data.shape[1],
        height=data.shape[0],
    )


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def load_aoi_shapes(path: str | Path) -> List[Any]:
    """Return a list of Shapely geometry objects from a vector file."""
    if not _FIONA_OK:
        raise ImportError("fiona and shapely are required.")
    with fiona.open(Path(path), "r") as src:
        return [shape(f["geometry"]) for f in src if f["geometry"] is not None]


def raster_to_vector(
    raster: RasterData,
    output_path: str | Path,
    mask_value: float = 1.0,
    layer_name: str = "inundation_extent",
) -> None:
    """Vectorise a binary raster (cells == mask_value) to a polygon shapefile."""
    if not _RASTERIO_OK or not _FIONA_OK:
        raise ImportError("rasterio and fiona required for raster_to_vector.")
    from rasterio.features import shapes as rio_shapes
    binary = (raster.data == mask_value).astype("uint8")
    geoms = []
    for geom, val in rio_shapes(binary, transform=raster.transform):
        if int(val) == 1:
            geoms.append(shape(geom))
    if not geoms:
        log.warning("No inundation cells to vectorise.")
        return
    merged = unary_union(geoms)
    schema = {"geometry": "Polygon", "properties": {"area_m2": "float"}}
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with fiona.open(p, "w", driver="ESRI Shapefile", crs=raster.crs.to_dict(), schema=schema) as dst:
        if hasattr(merged, "geoms"):
            for geom in merged.geoms:
                dst.write({"geometry": mapping(geom), "properties": {"area_m2": geom.area}})
        else:
            dst.write({"geometry": mapping(merged), "properties": {"area_m2": merged.area}})
    log.info("Extent vector written → %s", p)
