"""
update_gee.py
Runs weekly via GitHub Actions.
Fetches latest glacier/lake values from GEE and uploads CSV to Google Drive.
"""

import ee
import pandas as pd
import os
import json
import requests
from datetime import datetime, timedelta

# ── AUTHENTICATE GEE FROM SECRET ────────────────────────────
creds_json = os.environ.get("EE_CREDENTIALS")
if not creds_json:
    raise ValueError("EE_CREDENTIALS secret not found!")

creds_dict = json.loads(creds_json)
cred_path = os.path.expanduser("~/.config/earthengine/credentials")
os.makedirs(os.path.dirname(cred_path), exist_ok=True)
with open(cred_path, "w") as f:
    json.dump(creds_dict, f)

print("✅ GEE credentials written")

ee.Initialize(project="glacier-24838")
print("✅ GEE Initialized")

# ── AOI: Rashun Valley ───────────────────────────────────────
AOI = ee.Geometry.Rectangle([71.85, 35.80, 72.20, 36.10])

# ── HELPER ───────────────────────────────────────────────────
def get_surface_values(start_date, end_date, label="current"):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(AOI)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .median()
            .clip(AOI))

    ndsi = s2.normalizedDifference(['B3', 'B11']).rename('NDSI')
    ndwi = s2.normalizedDifference(['B3', 'B8']).rename('NDWI')
    glacier_mask = ndsi.gt(0.3)
    water_mask   = ndwi.gt(0.2)

    aoi_area = AOI.area().divide(1e6).getInfo()

    glacier_area = (glacier_mask.multiply(ee.Image.pixelArea())
                    .reduceRegion(reducer=ee.Reducer.sum(), geometry=AOI,
                                  scale=10, maxPixels=1e10).get('NDSI'))
    glacier_km2  = ee.Number(glacier_area).divide(1e6).getInfo()
    glacier_pct  = round((glacier_km2 / aoi_area) * 100, 2)

    water_area = (water_mask.multiply(ee.Image.pixelArea())
                  .reduceRegion(reducer=ee.Reducer.sum(), geometry=AOI,
                                scale=10, maxPixels=1e10).get('NDWI'))
    lake_km2 = round(ee.Number(water_area).divide(1e6).getInfo(), 4)

    print(f"[{label}] Glacier: {glacier_pct}% | Lake: {lake_km2} km²")
    return glacier_pct, lake_km2

# ── FETCH VALUES ─────────────────────────────────────────────
today         = datetime.now()
current_start = (today - timedelta(days=60)).strftime('%Y-%m-%d')
current_end   = today.strftime('%Y-%m-%d')
prev_end      = (today - timedelta(days=305)).strftime('%Y-%m-%d')
prev_start    = (today - timedelta(days=365)).strftime('%Y-%m-%d')

print("⏳ Fetching current values...")
curr_glacier, curr_lake = get_surface_values(current_start, current_end, "CURRENT")

print("⏳ Fetching previous year values...")
prev_glacier, prev_lake = get_surface_values(prev_start, prev_end, "PREVIOUS")

# ── BUILD CSV ────────────────────────────────────────────────
df = pd.DataFrame([{
    'glacier_pct':      curr_glacier,
    'lake_area_km2':    curr_lake,
    'prev_glacier_pct': prev_glacier,
    'prev_lake_km2':    prev_lake,
    'last_updated':     today.strftime('%Y-%m-%d %H:%M'),
    'current_start':    current_start,
    'current_end':      current_end,
    'prev_start':       prev_start,
    'prev_end':         prev_end,
}])

csv_path = "latest_values.csv"
df.to_csv(csv_path, index=False)
print(f"\n✅ CSV created: {csv_path}")
print(df.to_string(index=False))

# ── UPLOAD TO GOOGLE DRIVE via API ───────────────────────────
drive_token = os.environ.get("GOOGLE_DRIVE_TOKEN")
file_id     = "1IdDkqsp-vgkgdBaOeLzdFmspSJc7-2vp"

if drive_token:
    headers = {"Authorization": f"Bearer {drive_token}"}

    # Update existing file content
    upload_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
    with open(csv_path, "rb") as f:
        response = requests.patch(
            upload_url,
            headers={**headers, "Content-Type": "text/csv"},
            data=f
        )

    if response.status_code == 200:
        print(f"✅ Google Drive updated! File ID: {file_id}")
    else:
        print(f"⚠️ Drive upload failed: {response.status_code} — {response.text}")
else:
    print("⚠️ GOOGLE_DRIVE_TOKEN not set — CSV not uploaded to Drive")

print("\n🏁 Done!")
