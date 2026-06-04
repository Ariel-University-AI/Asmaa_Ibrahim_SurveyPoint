"""
run_test_data1.py — חילוץ + השוואה ל-coordinates_1.CSV
הרצה: python run_test_data1.py
"""
import sys, os, time, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Project3"))

import pandas as pd
from extractor import extract_with_gemini

# ── הגדרות ──────────────────────────────────────────────────────────────────
TIF_PATH = os.path.join(os.path.dirname(__file__), "DATA", "1", "Data1.TIF")
CSV_PATH = os.path.join(os.path.dirname(__file__), "DATA", "1", "coordinates_1.CSV")
OUT_PATH = os.path.join(os.path.dirname(__file__), "coordinates_extracted_new.csv")

# ── API Key ──────────────────────────────────────────────────────────────────
KEY_FILE = os.path.join(os.path.dirname(__file__), "key.txt")
if not os.path.exists(KEY_FILE):
    print("צרי קובץ key.txt עם ה-API Key שלך:")
    print(f"  echo AIzaSy...KEY > key.txt")
    sys.exit(1)
with open(KEY_FILE, encoding="utf-8") as f:
    api_key = f.read().strip()
if not api_key:
    print("key.txt ריק"); sys.exit(1)
print(f"Key: {api_key[:8]}...{api_key[-4:]} (length={len(api_key)})")

# ── טען TIF ──────────────────────────────────────────────────────────────────
print(f"\nטוען {TIF_PATH}...")
with open(TIF_PATH, "rb") as f:
    tif_bytes = f.read()
print(f"גודל קובץ: {len(tif_bytes)//1024} KB")

# ── חילוץ ────────────────────────────────────────────────────────────────────
print("\n=== מתחיל חילוץ ===")
t0 = time.time()

pages_done = [0]
def cb(done, total):
    pages_done[0] = done
    print(f"  {done}/{total}", end="\r")

df_ext = extract_with_gemini(tif_bytes, api_key=api_key, progress_cb=cb)

elapsed = time.time() - t0
print(f"\n\n=== חילוץ הושלם ===")
print(f"זמן:       {elapsed:.0f} שניות")
print(f"נקודות:    {len(df_ext)}")

# שמור תוצאה
df_ext.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
print(f"נשמר:      {OUT_PATH}")

if len(df_ext) == 0:
    print("לא חולצו נקודות — בדקי שגיאות למעלה")
    sys.exit(1)

# ── השוואה ───────────────────────────────────────────────────────────────────
print("\n=== השוואה ל-CSV מקורי ===")
orig = pd.read_csv(CSV_PATH, encoding="cp1255")
orig.columns = ["name", "Y", "X"]
orig["name"] = orig["name"].astype(str).str.strip()

ext = df_ext.copy()
ext.columns = [c if c != "שם נקודה" else "name" for c in ext.columns]
ext["name"] = ext["name"].astype(str).str.strip()

# זיהוי scale: מקומי (< 1000) vs מלא (> 100000)
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

matched   = orig_names & ext_names
only_orig = orig_names - ext_names
only_ext  = ext_names  - orig_names

TOL = 1.5
good, bad = [], []
for name in sorted(matched):
    yo, xo = orig_dict[name]
    ye, xe = ext_dict[name]
    if abs(yo - ye) < TOL and abs(xo - xe) < TOL:
        good.append(name)
    else:
        bad.append(name)

print(f"מקורי:           {len(orig)} נקודות")
print(f"חולצו:           {len(ext)} נקודות")
print(f"שמות משותפים:    {len(matched)}")
print(f"קואורדינטות OK:  {len(good)} / {len(orig)} = {len(good)/len(orig)*100:.1f}%")
print(f"קואורדינטות שונה:{len(bad)}")
print(f"חסרות לגמרי:     {len(only_orig)} — {sorted(only_orig)}")
print(f"עודפות (לא ב-CSV):{len(only_ext)}")

print(f"\n{'='*40}")
print(f"ציון סופי: {len(good)}/{len(orig)} = {len(good)/len(orig)*100:.1f}%")
print(f"{'='*40}")
