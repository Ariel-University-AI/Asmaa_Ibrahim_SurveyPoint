"""
extractor.py — חילוץ קואורדינטות מתיקי חישובים באמצעות Gemini Vision AI
"""

import re
import io
import numpy as np
import pandas as pd
from PIL import Image


def _is_valid_gemini_coord(v: float) -> bool:
    """פורמט תקין: 3 ספרות עשרוני (100-999) או 6 ספרות עשרוני (100000-999999)"""
    return (100.0 <= v < 1000.0) or (100_000.0 <= v < 1_000_000.0)


def extract_with_gemini(
    tif_bytes: bytes,
    api_key: str,
    progress_cb=None,
) -> pd.DataFrame:
    """
    שולח דפים ל-Gemini, מחזיר קואורדינטות.
    """
    import requests, base64, json, time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    HDR = {"x-goog-api-key": api_key} if not api_key.startswith("AIzaSy") else {}
    QP  = f"?key={api_key}" if api_key.startswith("AIzaSy") else ""

    try:
        lst = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models{QP}",
            headers=HDR, timeout=10)
        lst.raise_for_status()
        avail = [m['name'].split('/')[-1] for m in lst.json().get('models', [])
                 if 'generateContent' in m.get('supportedGenerationMethods', [])
                 and 'flash' in m['name']]
        v25 = [m for m in avail if '2.5-flash' in m and 'pro' not in m]
        GEMINI_MODEL = (v25 or avail or ["gemini-2.5-flash"])[0]
    except Exception:
        GEMINI_MODEL = "gemini-2.5-flash"

    API_URL = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent{QP}")
    print(f"Model: {GEMINI_MODEL}")

    PROMPT = """זהו דף מתיק חישובים הנדסי ישראלי.

חלץ קואורדינטות מכל טבלה בדף.

═══ זיהוי עמודות ═══
Y / X | E או East (=X) / N או North (=Y) | א / מ
Y = צפון, X = מזרח — אל תחליף לעולם!
אם אין כותרות: ITM — Y=100k-300k, X=400k-900k. שני ערכים זהי טווח: הקטן=Y, הגדול=X.

═══ כללי שמות ═══
עד 8 תווים, מספרים + אותיות לועזיות. אסור: עברית, ΔY/ΔX, ערכים שליליים, סיכומים.

═══ אסור לחלץ ═══
עמודת גובה (H / Height / גובה) — חלץ Y ו-X בלבד, לא גובה!

═══ סיווג נקודות — חובה לכל נקודה ═══
"known" = נקודת ייחוס ברשת: 831H, 833HL, X1, X2, X1R — בד"כ בראש הדף
"old"   = נקודה מסקר קודם — מסומנת "ישן"/"קודם" בדף, או ברשימה נפרדת
"new"   = כל שאר הנקודות (ברירת מחדל)

═══ דיוק ═══
3 ספרות אחרי הנקודה. 618730 → 618730.000

החזר JSON בלבד:
{"has_headers": true, "points": [
  {"name":"831H","Y":0.0,"X":0.0,"type":"known"},
  {"name":"15",  "Y":0.0,"X":0.0,"type":"new"}
]}
אין קואורדינטות → {"has_headers": false, "points": []}"""

    PROMPT_CONTINUATION = """זהו דף המשך של טבלת קואורדינטות — אין כותרות עמודות בדף זה.

הטבלה התחילה בדף קודם. חלץ לפי אותו סדר עמודות: שם נקודה | Y (צפון) | X (מזרח).
טווחי ITM: Y=100k-300k, X=400k-900k. דיוק: 3 ספרות.
עמודת גובה (H) — התעלם ממנה לחלוטין.
סיווג: known/old/new כרגיל.

החזר JSON: {"has_headers": false, "points": [{"name":"שם","Y":0.0,"X":0.0,"type":"new"}]}
אין נתונים → {"has_headers": false, "points": []}"""

    src = Image.open(io.BytesIO(tif_bytes))
    n_pages = getattr(src, 'n_frames', 1)
    print(f"TIF: {n_pages} pages")

    pages_b64 = {}
    for p in range(n_pages):
        src.seek(p)
        arr = np.array(src.convert('L'))
        black_ratio = (arr < 128).mean()
        if black_ratio < 0.01 or black_ratio > 0.85:
            pages_b64[p] = None
            continue
        buf = io.BytesIO()
        src.convert('RGB').save(buf, format='JPEG', quality=80)
        pages_b64[p] = base64.b64encode(buf.getvalue()).decode()

    done = [0]
    t_global = time.time()

    def _send_page(p):
        img_b64 = pages_b64.get(p)
        if img_b64 is None:
            return p, [], True

        t0 = time.time()
        offset = t0 - t_global
        has_headers = True
        print(f"P{p+1}: START (+{offset:.1f}s, {len(img_b64)//1024}KB)")

        payload = {"contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": PROMPT}
        ]}]}

        pts = []
        for attempt in range(2):
            try:
                resp = requests.post(API_URL, json=payload, headers=HDR, timeout=70)
                if resp.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"P{p+1}: 429, wait {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    print(f"P{p+1}: HTTP {resp.status_code}")
                    break
                raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
                has_headers = True
                point_list = []
                try:
                    ds, de = raw.find('{'), raw.rfind('}')
                    if ds != -1 and de > ds:
                        obj = json.loads(raw[ds:de+1])
                        has_headers = obj.get('has_headers', True)
                        point_list  = obj.get('points', [])
                except Exception:
                    pass
                if not point_list:
                    ls, le = raw.find('['), raw.rfind(']')
                    if ls != -1 and le > ls:
                        try: point_list = json.loads(raw[ls:le+1])
                        except Exception: point_list = []

                TYPE_HE = {'known': 'ידועה', 'old': 'ישנה', 'new': 'חדשה'}
                for item in point_list:
                    try:
                        name = str(item.get('name') or item.get('nome') or
                                   item.get('שם') or item.get('point') or '').strip()
                        if not name or len(name) > 8: continue
                        if not re.match(r'^[0-9A-Za-z]{1,8}$', name): continue
                        y = float(str(item.get('Y', item.get('y', 0))).replace(',', '.'))
                        x = float(str(item.get('X', item.get('x', 0))).replace(',', '.'))
                        if 1000 <= y < 10000: y = float(str(y)[1:])
                        if 1000 <= x < 10000: x = float(str(x)[1:])
                        if y < 10000 and abs(y - x) < 1: continue
                        if not (name and y > 0 and x > 0): continue
                        pt = item.get('type', '')
                        sug = TYPE_HE.get(pt, '')
                        pts.append({'שם נקודה': name, 'Y': y, 'X': x, 'סוג': sug})
                    except Exception:
                        pass
                elapsed = time.time() - t0
                print(f"P{p+1}: DONE {len(pts)} pts ({elapsed:.1f}s)"
                      + ("" if has_headers else " [no-header]"))
                break
            except requests.exceptions.Timeout:
                print(f"P{p+1}: timeout ({attempt+1}/2)")
                if attempt == 0: time.sleep(3)
            except Exception as ex:
                print(f"P{p+1} err: {ex}")
                break
        return p, pts, has_headers

    BATCH = 5
    results = {}
    result_meta = {}

    for batch_start in range(0, n_pages, BATCH):
        batch = list(range(batch_start, min(batch_start + BATCH, n_pages)))
        bt0 = time.time()
        print(f"\n-- Batch {batch_start//BATCH+1} -- pages {[p+1 for p in batch]}")
        with ThreadPoolExecutor(max_workers=BATCH) as pool:
            futures = {}
            for i, p in enumerate(batch):
                futures[pool.submit(_send_page, p)] = p
                if i < len(batch) - 1:
                    time.sleep(0.8)
            for fut in as_completed(futures):
                p, pts, has_hdr = fut.result()
                results[p] = pts
                result_meta[p] = has_hdr
                done[0] += 1
                if progress_cb:
                    progress_cb(done[0], n_pages)
        print(f"-- Batch {batch_start//BATCH+1} done: {time.time()-bt0:.1f}s --")
        if batch_start + BATCH < n_pages:
            time.sleep(1)

    MIN_SIZE_RETRY = 400 * 1024 // 4 * 3
    retry_pages = [p for p in range(n_pages)
                   if len(results.get(p, [])) == 0
                   and pages_b64.get(p) is not None
                   and len(pages_b64[p]) > MIN_SIZE_RETRY]
    if retry_pages:
        print(f"\n-- Adaptive retry: {len(retry_pages)} pages with 0 results --")
        time.sleep(2)
        retry_batch = []
        for p in retry_pages:
            retry_batch.append(p)
            if len(retry_batch) == BATCH or p == retry_pages[-1]:
                with ThreadPoolExecutor(max_workers=BATCH) as pool:
                    futures = {pool.submit(_send_page, pp): pp for pp in retry_batch}
                    for fut in as_completed(futures):
                        pp, pts, has_hdr = fut.result()
                        if pts:
                            results[pp] = pts
                            result_meta[pp] = has_hdr
                            print(f"  Retry P{pp+1}: {len(pts)} pts recovered")
                retry_batch = []
                time.sleep(1)

    continuation_pages = [
        p for p in range(n_pages)
        if not result_meta.get(p, True)
        and len(results.get(p, [])) == 0
        and pages_b64.get(p) is not None
    ]
    if continuation_pages:
        print(f"\n-- Continuation pass: {len(continuation_pages)} header-less pages --")
        for p in continuation_pages:
            payload_c = {"contents": [{"parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": pages_b64[p]}},
                {"text": PROMPT_CONTINUATION}
            ]}]}
            try:
                resp = requests.post(API_URL, json=payload_c, headers=HDR, timeout=70)
                if resp.status_code == 200:
                    raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    ds, de = raw.find('{'), raw.rfind('}')
                    if ds != -1:
                        obj = json.loads(raw[ds:de+1])
                        pts_c = []
                        TYPE_HE = {'known':'ידועה','old':'ישנה','new':'חדשה'}
                        for item in obj.get('points', []):
                            try:
                                name = str(item.get('name','')).strip()
                                if not name or len(name) > 8: continue
                                if not re.match(r'^[0-9A-Za-z]{1,8}$', name): continue
                                y = float(str(item.get('Y',0)).replace(',','.'))
                                x = float(str(item.get('X',0)).replace(',','.'))
                                if y > 0 and x > 0:
                                    pt = item.get('type','')
                                    pts_c.append({'שם נקודה': name, 'Y': y, 'X': x,
                                                  'סוג': TYPE_HE.get(pt,'')})
                            except Exception: pass
                        if pts_c:
                            results[p] = pts_c
                            print(f"  Continuation P{p+1}: {len(pts_c)} pts recovered")
            except Exception as ex:
                print(f"  Continuation P{p+1} err: {ex}")
            time.sleep(4)

    all_points = [pt for p in range(n_pages) for pt in results.get(p, [])]
    print(f"Done: {len(all_points)} total points")

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X'])

    y_med = df['Y'].median()
    x_med = df['X'].median()
    if y_med > x_med * 1.5:
        df = df.rename(columns={'Y': '_tmp', 'X': 'Y'}).rename(columns={'_tmp': 'X'})
        y_med, x_med = x_med, y_med
    if x_med > 400_000:
        mask = df['Y'] > df['X']
        if mask.sum() > 0:
            df.loc[mask, ['Y', 'X']] = df.loc[mask, ['X', 'Y']].values

    best = []
    has_sug = 'סוג' in df.columns
    for name, grp in df.groupby('שם נקודה', sort=False):
        y_bucket = grp['Y'].round(1).mode().iloc[0] if len(grp) else grp['Y'].iloc[0]
        x_bucket = grp['X'].round(1).mode().iloc[0] if len(grp) else grp['X'].iloc[0]
        mask = (grp['Y'].round(1) == round(float(y_bucket), 1)) & \
               (grp['X'].round(1) == round(float(x_bucket), 1))
        row = grp[mask].iloc[0] if mask.any() else grp.iloc[0]
        entry = {
            'שם נקודה': name,
            'Y': round(float(row['Y']), 3),
            'X': round(float(row['X']), 3),
        }
        if has_sug:
            entry['סוג'] = row.get('סוג', '')
        best.append(entry)
    return pd.DataFrame(best)


def spatial_match_to_reference(
    extracted_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    threshold: float = 2.0,
) -> pd.DataFrame:
    if extracted_df.empty or reference_df.empty:
        return extracted_df

    ref = reference_df.copy()
    ref_name_col = [c for c in ref.columns if c not in ['Y', 'X']][0]
    ref = ref.rename(columns={ref_name_col: 'name_ref', 'Y': 'Y_ref', 'X': 'X_ref'})
    ref['Y_ref'] = pd.to_numeric(ref['Y_ref'], errors='coerce')
    ref['X_ref'] = pd.to_numeric(ref['X_ref'], errors='coerce')
    ref = ref.dropna().reset_index(drop=True)

    ext = extracted_df.copy()
    ext_name_col = [c for c in ext.columns if c not in ['Y', 'X']][0]
    ext['Y'] = pd.to_numeric(ext['Y'], errors='coerce')
    ext['X'] = pd.to_numeric(ext['X'], errors='coerce')
    ext = ext.dropna(subset=['Y', 'X']).reset_index(drop=True)

    y_med_ext = ext['Y'].median()
    y_med_ref = ref['Y_ref'].median()
    if y_med_ext < 10000 and y_med_ref > 10000:
        y_offset = round(y_med_ref/1000)*1000 - round(y_med_ext/1000)*1000
        x_offset = round(ref['X_ref'].median()/1000)*1000 - round(ext['X'].median()/1000)*1000
    else:
        y_offset, x_offset = 0, 0

    ref_y = ref['Y_ref'].values
    ref_x = ref['X_ref'].values
    ref_names = ref['name_ref'].values
    used = set()
    rows = []

    for _, row in ext.iterrows():
        y_full = row['Y'] + y_offset
        x_full = row['X'] + x_offset
        dists = ((ref_y - y_full) ** 2 + (ref_x - x_full) ** 2) ** 0.5
        idx = int(dists.argmin())
        dist = float(dists[idx])
        if dist <= threshold and idx not in used:
            used.add(idx)
            rows.append({'שם נקודה': ref_names[idx], 'Y': float(ref_y[idx]), 'X': float(ref_x[idx])})
        else:
            rows.append({'שם נקודה': row[ext_name_col], 'Y': row['Y'], 'X': row['X']})

    return pd.DataFrame(rows).drop_duplicates('שם נקודה').reset_index(drop=True)


def extract_from_pdf(file_bytes: bytes) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])
    all_points = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                for row in table:
                    if not row or len(row) < 3: continue
                    name = str(row[0] or '').strip()
                    try:
                        y = float(str(row[1]).replace(',', '.'))
                        x = float(str(row[2]).replace(',', '.'))
                        if name and y > 0 and x > 0 and abs(y - x) > 1:
                            all_points.append({'שם נקודה': name, 'Y': y, 'X': x})
                    except Exception:
                        continue
    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])
    return pd.DataFrame(all_points).drop_duplicates('שם נקודה').reset_index(drop=True)


def extract_from_tif(file_bytes: bytes, progress_cb=None, **kwargs) -> pd.DataFrame:
    """Stub - Tesseract not available on cloud. Use Gemini instead."""
    raise ImportError("Tesseract OCR not available. Please provide a Gemini API Key.")
