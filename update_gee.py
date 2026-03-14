"""
update_gee.py — Daily Glacier Data Update
Runs via GitHub Actions. Uses Planet API (primary) or GEE Sentinel-2 (fallback).
"""

import os
import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# ── CONFIG ───────────────────────────────────────────────────
PLANET_API_KEY  = os.environ.get("PLANET_API_KEY", "")
GEE_CREDENTIALS = os.environ.get("EE_CREDENTIALS", "")
DRIVE_TOKEN     = os.environ.get("GOOGLE_DRIVE_TOKEN", "")
FILE_ID         = "1IdDkqsp-vgkgdBaOeLzdFmspSJc7-2vp"

LON_MIN, LAT_MIN = 71.85, 35.80
LON_MAX, LAT_MAX = 72.20, 36.10

AOI_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [LON_MIN, LAT_MIN], [LON_MAX, LAT_MIN],
        [LON_MAX, LAT_MAX], [LON_MIN, LAT_MAX],
        [LON_MIN, LAT_MIN]
    ]]
}

# ── GEE INIT ─────────────────────────────────────────────────
def init_gee():
    """Write credentials file and initialize GEE"""
    if not GEE_CREDENTIALS:
        print("❌ EE_CREDENTIALS secret is empty or not set!")
        return False
    try:
        # Parse the JSON credentials
        creds_dict = json.loads(GEE_CREDENTIALS)
        print(f"✅ Credentials parsed — client_id: {creds_dict.get('client_id','?')[:30]}...")

        # Write to the expected location
        cred_path = os.path.expanduser("~/.config/earthengine/credentials")
        os.makedirs(os.path.dirname(cred_path), exist_ok=True)
        with open(cred_path, "w") as f:
            json.dump(creds_dict, f)
        print(f"✅ Credentials written to {cred_path}")

        # Import and initialize AFTER writing credentials
        import ee
        ee.Initialize(project="glacier-24838")
        print("✅ GEE Initialized successfully")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in EE_CREDENTIALS: {e}")
        return False
    except Exception as e:
        print(f"❌ GEE init failed: {e}")
        return False

# ── GEE VALUES ───────────────────────────────────────────────
def get_gee_values(start_date, end_date, label=""):
    """Get glacier/lake metrics from GEE Sentinel-2"""
    import ee
    AOI = ee.Geometry.Rectangle([71.85, 35.80, 72.20, 36.10])

    try:
        s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                .filterBounds(AOI)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                .median()
                .clip(AOI))

        ndsi = s2.normalizedDifference(['B3', 'B11']).rename('NDSI')
        ndwi = s2.normalizedDifference(['B3', 'B8']).rename('NDWI')

        aoi_area = AOI.area().divide(1e6).getInfo()

        glacier_area = (ndsi.gt(0.3)
                        .multiply(ee.Image.pixelArea())
                        .reduceRegion(reducer=ee.Reducer.sum(),
                                      geometry=AOI, scale=10,
                                      maxPixels=1e10).get('NDSI'))
        glacier_km2 = ee.Number(glacier_area).divide(1e6).getInfo()
        glacier_pct = round((glacier_km2 / aoi_area) * 100, 2)

        lake_area = (ndwi.gt(0.2)
                     .multiply(ee.Image.pixelArea())
                     .reduceRegion(reducer=ee.Reducer.sum(),
                                   geometry=AOI, scale=10,
                                   maxPixels=1e10).get('NDWI'))
        lake_km2 = round(ee.Number(lake_area).divide(1e6).getInfo(), 4)

        print(f"[GEE {label}] Glacier: {glacier_pct}% | Lake: {lake_km2} km²")
        return glacier_pct, lake_km2

    except Exception as e:
        print(f"❌ GEE computation error: {e}")
        return None, None

# ── PLANET SEARCH ────────────────────────────────────────────
def search_planet_scenes(days_back=30, max_cloud=0.3):
    """Search for latest PlanetScope scenes"""
    if not PLANET_API_KEY:
        print("⚠️ No PLANET_API_KEY set")
        return []

    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    payload = {
        "item_types": ["PSScene"],
        "filter": {
            "type": "AndFilter",
            "config": [
                {"type": "GeometryFilter",  "field_name": "geometry",    "config": AOI_GEOJSON},
                {"type": "DateRangeFilter", "field_name": "acquired",    "config": {"gte": start}},
                {"type": "RangeFilter",     "field_name": "cloud_cover", "config": {"lte": max_cloud}}
            ]
        }
    }
    try:
        r = requests.post("https://api.planet.com/data/v1/quick-search",
                          json=payload, auth=(PLANET_API_KEY, ""), timeout=30)
        if r.status_code == 200:
            features = r.json().get("features", [])
            print(f"✅ Planet: Found {len(features)} scenes")
            return features
        else:
            print(f"⚠️ Planet search: {r.status_code} — {r.text[:200]}")
    except Exception as e:
        print(f"⚠️ Planet search error: {e}")
    return []

# ── PLANET DOWNLOAD & PROCESS ────────────────────────────────
def activate_and_download_scene(scene_id):
    import time
    auth = (PLANET_API_KEY, "")
    base_url = f"https://api.planet.com/data/v1/item-types/PSScene/items/{scene_id}/assets"

    for asset_type in ["ortho_analytic_4b_sr", "ortho_analytic_4b"]:
        try:
            r = requests.get(base_url, auth=auth, timeout=30)
            if r.status_code != 200:
                continue
            assets = r.json()
            if asset_type not in assets:
                continue

            asset = assets[asset_type]
            if asset["status"] != "active":
                print(f"⏳ Activating {scene_id}...")
                requests.get(asset["_links"]["activate"], auth=auth, timeout=30)
                for i in range(20):
                    time.sleep(30)
                    r2   = requests.get(base_url, auth=auth, timeout=30)
                    asset = r2.json().get(asset_type, {})
                    print(f"   Status: {asset.get('status')} ({(i+1)*30}s)")
                    if asset.get("status") == "active":
                        break

            if asset.get("status") == "active":
                print(f"⬇️ Downloading {scene_id}...")
                r3 = requests.get(asset["location"], auth=auth, timeout=180, stream=True)
                if r3.status_code == 200:
                    print("✅ Download complete")
                    return BytesIO(r3.content)
        except Exception as e:
            print(f"⚠️ Asset {asset_type} error: {e}")
    return None

def compute_metrics_from_planet(scene_bytes):
    try:
        import rasterio
        from rasterio.io import MemoryFile
        with MemoryFile(scene_bytes) as memfile:
            with memfile.open() as ds:
                green = ds.read(2).astype(float)
                red   = ds.read(3).astype(float)
                nir   = ds.read(4).astype(float)
                eps   = 1e-10
                ndsi  = (green - nir) / (green + nir + eps)
                ndwi  = (green - nir) / (green + nir + eps)
                ndvi  = (nir - red)   / (nir + red + eps)
                pix   = ds.res[0] * ds.res[1]
                total = (green.size * pix) / 1e6
                g_pct = round((np.sum((ndsi > 0.3) & (ndvi < 0.1)) * pix / 1e6 / total) * 100, 2)
                l_km2 = round(np.sum(ndwi > 0.2) * pix / 1e6, 4)
                print(f"✅ Planet — Glacier: {g_pct}% | Lake: {l_km2} km²")
                return g_pct, l_km2
    except Exception as e:
        print(f"⚠️ Planet processing error: {e}")
        return None, None

# ── UPLOAD TO DRIVE ──────────────────────────────────────────
def upload_to_drive(csv_path):
    if not DRIVE_TOKEN:
        print("⚠️ No GOOGLE_DRIVE_TOKEN — skipping Drive upload")
        return
    url = f"https://www.googleapis.com/upload/drive/v3/files/{FILE_ID}?uploadType=media"
    with open(csv_path, "rb") as f:
        r = requests.patch(url,
            headers={"Authorization": f"Bearer {DRIVE_TOKEN}",
                     "Content-Type": "text/csv"},
            data=f, timeout=30)
    if r.status_code == 200:
        print("✅ Google Drive updated!")
    else:
        print(f"⚠️ Drive upload failed: {r.status_code} — {r.text[:200]}")

# ── MAIN ─────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"🏔️  Reshun Glacier Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Check secrets
    print(f"\n🔑 Secrets check:")
    print(f"   EE_CREDENTIALS:      {'✅ SET' if GEE_CREDENTIALS else '❌ NOT SET'}")
    print(f"   GOOGLE_DRIVE_TOKEN:  {'✅ SET' if DRIVE_TOKEN     else '❌ NOT SET'}")
    print(f"   PLANET_API_KEY:      {'✅ SET' if PLANET_API_KEY  else '❌ NOT SET'}")

    today         = datetime.now()
    current_start = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    current_end   = today.strftime('%Y-%m-%d')
    prev_start    = (today - timedelta(days=365)).strftime('%Y-%m-%d')
    prev_end      = (today - timedelta(days=305)).strftime('%Y-%m-%d')

    curr_glacier = curr_lake = prev_glacier = prev_lake = None
    data_source  = "unknown"

    # ── 1. Try Planet ─────────────────────────────────────────
    if PLANET_API_KEY:
        print("\n🌍 Step 1: Trying PlanetScope...")
        scenes = search_planet_scenes(days_back=30, max_cloud=0.3)
        if scenes:
            latest     = scenes[0]
            scene_id   = latest["id"]
            scene_date = latest["properties"]["acquired"][:10]
            cloud      = latest["properties"]["cloud_cover"]
            print(f"📸 Latest: {scene_id} | {scene_date} | Cloud: {cloud:.0%}")
            scene_bytes = activate_and_download_scene(scene_id)
            if scene_bytes:
                curr_glacier, curr_lake = compute_metrics_from_planet(scene_bytes)
                if curr_glacier is not None:
                    data_source = f"PlanetScope ({scene_date})"

    # ── 2. Fallback to GEE ───────────────────────────────────
    if curr_glacier is None:
        print("\n🛰️ Step 2: Falling back to GEE Sentinel-2...")
        if init_gee():
            curr_glacier, curr_lake = get_gee_values(
                current_start, current_end, "CURRENT")
            data_source = "Sentinel-2/GEE"

    # ── 3. Previous year from GEE ────────────────────────────
    print("\n⏳ Step 3: Fetching previous year from GEE...")
    if init_gee():
        prev_glacier, prev_lake = get_gee_values(prev_start, prev_end, "PREVIOUS")

    # ── 4. Validate ──────────────────────────────────────────
    if curr_glacier is None:
        print("\n❌ FATAL: Could not get current values from any source!")
        raise SystemExit(1)

    # ── 5. Save CSV ──────────────────────────────────────────
    df = pd.DataFrame([{
        'glacier_pct':      curr_glacier,
        'lake_area_km2':    curr_lake    or 0.0,
        'prev_glacier_pct': prev_glacier or 60.8,
        'prev_lake_km2':    prev_lake    or 0.039,
        'last_updated':     today.strftime('%Y-%m-%d %H:%M'),
        'data_source':      data_source,
        'current_start':    current_start,
        'current_end':      current_end,
    }])

    df.to_csv("latest_values.csv", index=False)
    print(f"\n✅ CSV saved:")
    print(df.to_string(index=False))

    # ── 6. Upload ────────────────────────────────────────────
    upload_to_drive("latest_values.csv")

    print("\n🏁 Done!")

if __name__ == "__main__":
    main()
