# Python 3
from datetime import datetime, timezone
from math import radians, tan, sin, cos, sqrt, asin
from skyfield.api import EarthSatellite, load

def compute_product_metrics(product: dict) -> dict:
    """
    Compute satellite image metrics from a product dictionary.
    Returns all values as native Python types (float, int, str) including FOV.
    """

    # --- image dimensions ---
    proj = product.get('projection_cfg', {})
    image_width = int(proj.get('image_width'))
    timestamps = product.get('timestamps', [])
    image_height = len(timestamps)
    if image_height == 0:
        raise ValueError("no timestamps found")

    # --- midtime ---
    mid_ts = 0.5 * (timestamps[0] + timestamps[-1])
    mid_datetime = datetime.fromtimestamp(mid_ts, tz=timezone.utc)

    # --- TLE and satellite ---
    tle = product.get('tle', {})
    line1 = tle.get('line1')
    line2 = tle.get('line2')
    name = tle.get('name', 'sat')
    if not line1 or not line2:
        raise ValueError("TLE lines missing")
    sat = EarthSatellite(line1, line2, name)
    ts_sf = load.timescale()

    # --- helper: POSIX -> Skyfield time ---
    def to_sf_time(posix_ts):
        dt = datetime.fromtimestamp(posix_ts, tz=timezone.utc)
        return ts_sf.utc(dt.year, dt.month, dt.day,
                         dt.hour, dt.minute, dt.second + dt.microsecond/1e6)

    # --- mid subpoint ---
    sub_mid = sat.at(to_sf_time(mid_ts)).subpoint()
    mid_subpoint = {
        "lat_deg": float(sub_mid.latitude.degrees),
        "lon_deg": float(sub_mid.longitude.degrees),
        "alt_km": float(sub_mid.elevation.km)
    }

    # --- first and last subpoints ---
    sub0 = sat.at(to_sf_time(timestamps[0])).subpoint()
    subN = sat.at(to_sf_time(timestamps[-1])).subpoint()
    first_subpoint = {
        "lat_deg": float(sub0.latitude.degrees),
        "lon_deg": float(sub0.longitude.degrees)
    }
    last_subpoint = {
        "lat_deg": float(subN.latitude.degrees),
        "lon_deg": float(subN.longitude.degrees)
    }

    # --- haversine along-track length ---
    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0  # Earth radius km
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi/2.0)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2.0)**2
        c = 2*asin(sqrt(a))
        return R * c

    along_track_length_km = haversine_km(sub0.latitude.degrees, sub0.longitude.degrees,
                                         subN.latitude.degrees, subN.longitude.degrees)
    pix_along_m = (along_track_length_km * 1000.0) / image_height

    # --- across-track swath and pixel size ---
    scan_angle_deg = proj.get('scan_angle', 0.0)
    half_angle_rad = radians(scan_angle_deg / 2.0)
    swath_km = 2.0 * float(sub_mid.elevation.km) * tan(half_angle_rad) if scan_angle_deg else None
    pix_across_m = (swath_km * 1000.0) / image_width if swath_km else None

    # --- total area and per-pixel area ---
    area_km2 = swath_km * along_track_length_km if swath_km else None
    per_pixel_km2 = (pix_along_m * pix_across_m) / 1e6 if pix_across_m else None

    # --- FOV (degrees) ---
    fov_deg = float(scan_angle_deg) if scan_angle_deg else None

    # --- assemble metrics ---
    metrics = {
        "image_width_px": int(image_width),
        "image_height_px": int(image_height),
        "mid_datetime": mid_datetime.isoformat(),
        "mid_subpoint": mid_subpoint,
        "first_subpoint": first_subpoint,
        "last_subpoint": last_subpoint,
        "along_track_length_km": float(along_track_length_km),
        "along_track_pixel_size_m": float(pix_along_m),
        "across_track_swath_km": float(swath_km) if swath_km else None,
        "across_track_pixel_size_m": float(pix_across_m) if pix_across_m else None,
        "total_ground_area_km2": float(area_km2) if area_km2 else None,
        "per_pixel_area_km2": float(per_pixel_km2) if per_pixel_km2 else None,
        "fov_deg": fov_deg
    }

    return metrics

metrics = compute_product_metrics(product)
metrics