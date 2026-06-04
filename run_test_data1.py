"""
run_test_data1.py - Extract + compare vs coordinates_1.CSV
Run: python run_test_data1.py
"""
import sys, os, time, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Project3"))

import pandas as pd
from extractor import extract_with_gemini

# Dataset number — change to 1/2/3/4
DATASET = "4"

DATA_DIR = os.path.join(os.path.dirname(__file__), "DATA", DATASET)
TIF_PATH = next((os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
                 if f.lower().endswith(('.tif', '.tiff'))), None)
CSV_PATH = next((os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
                 if f.lower().endswith(('.csv'))), None)
OUT_PATH = os.path.join(os.path.dirname(__file__), f"coordinates_extracted_{DATASET}.csv")

if not TIF_PATH or not os.path.exists(TIF_PATH):
    print(f"No TIF found in DATA/{DATASET}/"); sys.exit(1)
if not CSV_PATH or not os.path.exists(CSV_PATH):
    print(f"No CSV found in DATA/{DATASET}/"); sys.exit(1)
print(f"Dataset {DATASET}: {os.path.basename(TIF_PATH)} vs {os.path.basename(CSV_PATH)}")

# API Key from key.txt
KEY_FILE = os.path.join(os.path.dirname(__file__), "key.txt")
if not os.path.exists(KEY_FILE):
    print("Create key.txt with your API key: echo YOUR_KEY > key.txt")
    sys.exit(1)
with open(KEY_FILE, encoding="utf-8") as f:
    api_key = f.read().strip()
if not api_key:
    print("key.txt is empty"); sys.exit(1)
print(f"Key: {api_key[:8]}...{api_key[-4:]} (length={len(api_key)})")

# Load TIF
print(f"\nLoading {TIF_PATH}...")
with open(TIF_PATH, "rb") as f:
    tif_bytes = f.read()
print(f"File size: {len(tif_bytes)//1024} KB")

# Count TIF pages
try:
    from PIL import Image as _PIL
    _s = _PIL.open(io.BytesIO(tif_bytes))
    print(f"Pages: {getattr(_s,'n_frames',1)}")
except Exception:
    pass

# Extract
print("\n=== Starting extraction ===")
t0 = time.time()

def cb(done, total):
    print(f"  {done}/{total}", end="\r")

df_ext = extract_with_gemini(tif_bytes, api_key=api_key, progress_cb=cb)

elapsed = time.time() - t0
print(f"\n\n=== Extraction done ===")
print(f"Time:   {elapsed:.0f} seconds")
print(f"Points: {len(df_ext)}")

df_ext.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
print(f"Saved:  {OUT_PATH}")

if len(df_ext) == 0:
    print("No points extracted - check errors above")
    sys.exit(1)

# Compare vs reference CSV
print("\n=== Comparison vs reference CSV ===")
orig = pd.read_csv(CSV_PATH, encoding="cp1255")
orig.columns = ["name", "Y", "X"]
orig["name"] = orig["name"].astype(str).str.strip()

ext = df_ext.copy()
name_col = ext.columns[0]
ext = ext.rename(columns={name_col: "name"})
ext["name"] = ext["name"].astype(str).str.strip()

y_med_ext = ext["Y"].median()
y_med_ref = orig["Y"].median()
if y_med_ext < 10000 and y_med_ref > 10000:
    y_off = round(y_med_ref / 1000) * 1000 - round(y_med_ext / 1000) * 1000
    x_off = round(orig["X"].median() / 1000) * 1000 - round(ext["X"].median() / 1000) * 1000
else:
    y_off, x_off = 0, 0

ext["Y_full"] = ext["Y"] + y_off
ext["X_full"] = ext["X"] + x_off

orig_dict = {r["name"]: (r["Y"], r["X"]) for _, r in orig.iterrows()}
ext_dict  = {r["name"]: (r["Y_full"], r["X_full"]) for _, r in ext.iterrows()}

orig_names = set(orig_dict.keys())
ext_names  = set(ext_dict.keys())
matched    = orig_names & ext_names
only_orig  = orig_names - ext_names
only_ext   = ext_names  - orig_names

TOL = 1.5
good, bad = [], []
for name in sorted(matched):
    yo, xo = orig_dict[name]
    ye, xe = ext_dict[name]
    if abs(yo - ye) < TOL and abs(xo - xe) < TOL:
        good.append(name)
    else:
        bad.append(name)

print(f"Reference:   {len(orig)} points")
print(f"Extracted:   {len(ext)} points")
print(f"Matched:     {len(matched)}")
print(f"Correct:     {len(good)} / {len(orig)} = {len(good)/len(orig)*100:.1f}%")
print(f"Wrong coords:{len(bad)}")
print(f"Missing:     {len(only_orig)} -- {sorted(only_orig)}")
print(f"Extra:       {len(only_ext)}")

print(f"\n{'='*40}")
print(f"SCORE: {len(good)}/{len(orig)} = {len(good)/len(orig)*100:.1f}%")
print(f"TIME:  {elapsed:.0f} seconds")
print(f"{'='*40}")
