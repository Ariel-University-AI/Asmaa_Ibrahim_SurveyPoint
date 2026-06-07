"""
run_test_all.py - Run extraction + comparison on all 4 datasets
Usage: python run_test_all.py
"""
import sys, os, time, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Project3"))

import pandas as pd
from extractor import extract_with_gemini

KEY_FILE = os.path.join(os.path.dirname(__file__), "key.txt")
if not os.path.exists(KEY_FILE):
    print("Create key.txt with your API key"); sys.exit(1)
with open(KEY_FILE, encoding="utf-8") as f:
    api_key = f.read().strip()
print(f"Key: {api_key[:8]}...{api_key[-4:]} (length={len(api_key)})")

ROOT = os.path.dirname(__file__)
DATASETS = {
    "1": {"tif": "DATA/1/Data1.TIF",  "csv": "DATA/1/coordinates_1.CSV",  "enc": "cp1255"},
    "2": {"tif": "DATA/2/Data2.TIF",  "csv": "DATA/2/coordinates_2.csv",  "enc": "utf-8"},
    "3": {"tif": "DATA/3/Data3.TIF",  "csv": "DATA/3/coordinates_3.csv",  "enc": "utf-8"},
    "4": {"tif": "DATA/4/Data4.TIF",  "csv": "DATA/4/coordinates_4.csv",  "enc": "utf-8"},
}
TOL = 0.10  # 10cm threshold

results = {}
total_start = time.time()

for ds, info in DATASETS.items():
    tif_path = os.path.join(ROOT, info["tif"])
    csv_path = os.path.join(ROOT, info["csv"])
    out_path = os.path.join(ROOT, f"coordinates_extracted_{ds}.csv")

    print(f"\n{'='*50}")
    print(f"Dataset {ds}: {os.path.basename(tif_path)}")
    print(f"{'='*50}")

    with open(tif_path, "rb") as f:
        tif_bytes = f.read()

    t0 = time.time()
    done = [0]
    def cb(d, t): done[0]=d; print(f"  {d}/{t}", end="\r")

    df_ext = extract_with_gemini(tif_bytes, api_key=api_key, progress_cb=cb)
    elapsed = time.time() - t0

    df_ext.to_csv(out_path, index=False, encoding="utf-8-sig", float_format="%.3f")
    print(f"\nExtracted: {len(df_ext)} pts | Time: {elapsed:.0f}s")

    # Compare
    for enc in [info["enc"], "utf-8-sig", "utf-8", "cp1255", "latin-1"]:
        try:
            orig = pd.read_csv(csv_path, encoding=enc)
            break
        except Exception:
            continue

    orig.columns = ["name","Y","X"]
    orig["name"] = orig["name"].astype(str).str.strip()
    orig["Y"] = pd.to_numeric(orig["Y"], errors="coerce")
    orig["X"] = pd.to_numeric(orig["X"], errors="coerce")
    orig = orig.dropna(subset=["Y","X"])

    ext = df_ext.copy()
    ext.columns = ["name","Y","X"]
    ext["name"] = ext["name"].astype(str).str.strip()

    # תיקון Y/X swap (כמו normalize_coords באפליקציה)
    y_med = ext["Y"].median(); x_med = ext["X"].median()
    if y_med > x_med * 1.5:
        ext[["Y","X"]] = ext[["X","Y"]].values
        y_med, x_med = x_med, y_med
    if x_med > 400_000:
        mask = ext["Y"] > ext["X"]
        ext.loc[mask, ["Y","X"]] = ext.loc[mask, ["X","Y"]].values

    # תיקון offset לקואורדינטות מקומיות
    y_off = x_off = 0
    if ext["Y"].median() < 10000 and orig["Y"].median() > 10000:
        y_off = round(orig["Y"].median()/1000)*1000 - round(ext["Y"].median()/1000)*1000
        x_off = round(orig["X"].median()/1000)*1000 - round(ext["X"].median()/1000)*1000
    ext["Y"] += y_off; ext["X"] += x_off

    od = {r["name"]:(r["Y"],r["X"]) for _,r in orig.iterrows()}
    ed = {r["name"]:(r["Y"],r["X"]) for _,r in ext.iterrows()}
    matched = set(od) & set(ed)
    missing = set(od) - set(ed)

    good = sum(1 for n in matched
               if abs(od[n][0]-ed[n][0]) < TOL and abs(od[n][1]-ed[n][1]) < TOL)

    pct = good/len(orig)*100
    results[ds] = {"good": good, "total": len(orig), "pct": pct,
                   "extracted": len(df_ext), "time": elapsed, "missing": len(missing)}

    print(f"SCORE: {good}/{len(orig)} = {pct:.1f}%  (TOL={TOL}m)")
    if missing:
        print(f"Missing: {sorted(missing)[:10]}")

print(f"\n{'='*50}")
print(f"SUMMARY (TOL={TOL}m)")
print(f"{'='*50}")
for ds, r in results.items():
    bar = "█" * int(r["pct"]/5)
    print(f"Data{ds}: {r['good']:3d}/{r['total']:3d} = {r['pct']:5.1f}%  {bar}  ({r['time']:.0f}s)")

total = sum(r["good"] for r in results.values())
denom = sum(r["total"] for r in results.values())
print(f"\nOVERALL: {total}/{denom} = {total/denom*100:.1f}%")
print(f"TOTAL TIME: {(time.time()-total_start)/60:.1f} min")
print(f"\nTIP: הריצי שוב כדי לשפר — Gemini משתנה בין ריצות.")
print(f"CSVs saved: " + " | ".join(f"coordinates_extracted_{ds}.csv" for ds in results))
