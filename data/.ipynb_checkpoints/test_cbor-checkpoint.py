import os
import cbor2
import json
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime
from skyfield.api import Loader, EarthSatellite, Topos, wgs84

# Skyfield setup
load = Loader('.')
ts = load.timescale()

# Observer location (example: Kielce, PL)
OBSERVER_LAT = -20.28333333
OBSERVER_LON = 57.55000000
OBSERVER_ELEV = 0  # meters

observer = Topos(latitude_degrees=OBSERVER_LAT,
                 longitude_degrees=OBSERVER_LON,
                 elevation_m=OBSERVER_ELEV)

# Find first .cbor file
cbor_file = None
for file in os.listdir('.'):
    if file.endswith('.cbor'):
        cbor_file = file
        break

if not cbor_file:
    print("No .cbor file found in this directory.")
    exit()

json_file = os.path.splitext(cbor_file)[0] + '.json'

# Convert CBOR → JSON
with open(cbor_file, 'rb') as f:
    data = cbor2.load(f)

with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Converted: {cbor_file} -> {json_file}")

# Extract TLE
tle = data.get("tle")
if not tle:
    print("No TLE found in CBOR/JSON.")
    exit()

satellite = EarthSatellite(tle['line1'], tle['line2'], tle['name'], ts)

# Extract timestamps
timestamps = data.get("timestamps")
if not timestamps:
    print("No timestamps found.")
    exit()

records = []

for t in timestamps:
    if not isinstance(t, (int, float)) or t < 0:
        continue
    dt = datetime.utcfromtimestamp(t)
    t_sf = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    difference = satellite - observer
    topocentric = difference.at(t_sf)
    alt, az, dist = topocentric.altaz()
    subpoint = wgs84.subpoint(satellite.at(t_sf))

    records.append({
        "Timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "Azimuth (deg)": round(az.degrees, 3),
        "Elevation (deg)": round(alt.degrees, 3),
        "Distance (km)": round(dist.km, 3),
        "Lat (deg)": round(subpoint.latitude.degrees, 4),
        "Lon (deg)": round(subpoint.longitude.degrees, 4)
    })

# Save to Excel
df = pd.DataFrame(records)
excel_file = os.path.splitext(cbor_file)[0] + "_pass_data.xlsx"
df.to_excel(excel_file, index=False)
print(f"Excel saved: {excel_file}")

# Plot satellite track on world map
plt.figure(figsize=(12, 6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_global()
ax.add_feature(cfeature.LAND)
ax.add_feature(cfeature.OCEAN)
ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS, linestyle=':')

ax.plot(df["Lon (deg)"], df["Lat (deg)"], 'r-', label="Satellite track")
ax.scatter(df["Lon (deg)"].iloc[0], df["Lat (deg)"].iloc[0], color='green', label='Start')
ax.scatter(df["Lon (deg)"].iloc[-1], df["Lat (deg)"].iloc[-1], color='blue', label='End')

plt.legend()
plt.title(f"Satellite Track: {tle['name']}")
map_file = os.path.splitext(cbor_file)[0] + "_map.png"
plt.savefig(map_file, dpi=300)
plt.close()

print(f"Map saved: {map_file}")
