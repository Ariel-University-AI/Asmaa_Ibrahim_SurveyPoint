"""
extractor.py — חילוץ קואורדינטות מתיקי חישובים (TIF/PDF)

תומך שלושה סוגי דפים:
  חשוב מצולע     — קואורדינטות ציר (Y @ 62-81%, X @ 81-92%)
  חשוב קואורדינטות — קואורדינטות בינים (Y @ 62-70%, X @ 73-80%)
  חשוב שטחים     — קואורדינטות פרטיות (Y,X פרוסים על כל הדף)
"""

import re
import io
import os
import numpy as np
import pandas as pd
from PIL import Image
from collections import defaultdict

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────────────────────────
#  הכנת תמונה
# ─────────────────────────────────────────────────────────────────────────────

def _prepare(img: Image.Image) -> np.ndarray:
    import PIL.ImageEnhance as IE
    img = img.convert('L')
    w, h = img.size
    # תמיד שנה ל-1600px — גם הקטנה (לאחידות)
    img = img.resize((1600, int(h * 1600 / w)), Image.LANCZOS)
    img = IE.Contrast(img).enhance(2.0)
    img = IE.Sharpness(img).enhance(2.0)
    return np.array(img.convert('RGB'))


def _has_content(img: Image.Image) -> bool:
    arr = np.array(img.convert('L'))
    black = (arr < 128).mean()
    return 0.02 <= black <= 0.75

# ─────────────────────────────────────────────────────────────────────────────
#  OCR
# ─────────────────────────────────────────────────────────────────────────────

def _ocr_full(arr: np.ndarray) -> list:
    """OCR כל הדף → [(cx, cy, text, conf)]"""
    from PIL import Image as _PIL
    img = _PIL.fromarray(arr)
    # OCR כללי ללא whitelist — חובה לזיהוי Sn/Cs ושמות נקודה
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT,
        lang='eng', config='--oem 1 --psm 11',
    )
    out = []
    for i in range(len(data['text'])):
        t = data['text'][i].strip()
        c = int(data['conf'][i])
        if not t or c < 15:
            continue
        cx = data['left'][i] + data['width'][i] // 2
        cy = data['top'][i] + data['height'][i] // 2
        out.append((cx, cy, t, c / 100.0))
    return out


def _ocr_strip(pil_img, psm=11, extra='') -> list:
    """OCR על פס → [(cx, cy, text, conf)]"""
    config = f'--oem 1 --psm {psm} {extra}'.strip()
    data = pytesseract.image_to_data(
        pil_img, output_type=pytesseract.Output.DICT,
        lang='eng', config=config,
    )
    out = []
    for i in range(len(data['text'])):
        t = data['text'][i].strip()
        c = int(data['conf'][i])
        if not t or c < 15:
            continue
        cx = data['left'][i] + data['width'][i] // 2
        cy = data['top'][i] + data['height'][i] // 2
        out.append((cx, cy, t, c / 100.0))
    return out

def _ocr_easyocr(arr: np.ndarray) -> list:
    """EasyOCR — פורמט אחיד [(cx, cy, text, conf)]"""
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        results = reader.readtext(arr, detail=1)
        out = []
        for bbox, text, conf in results:
            if conf < 0.2: continue
            cx = int(sum(p[0] for p in bbox) / 4)
            cy = int(sum(p[1] for p in bbox) / 4)
            out.append((cx, cy, text.strip(), float(conf)))
        return out
    except Exception:
        return []


def _ocr_combined(arr: np.ndarray) -> list:
    """
    משלב Tesseract + EasyOCR.
    מוסיף EasyOCR רק אם מותקן — מכפיל סיכוי לקריאה נכונה.
    מסיר כפילויות (אותו מיקום ±20px).
    """
    items_t = _ocr_full(arr)       # Tesseract (מהיר)
    items_e = _ocr_easyocr(arr)    # EasyOCR (מדויק יותר, איטי)

    merged = list(items_t)
    for cx2, cy2, text2, conf2 in items_e:
        # הוסף רק אם אין פריט קרוב מ-Tesseract
        dup = any(abs(cx2 - cx) < 20 and abs(cy2 - cy) < 15
                  for cx, cy, _, _ in items_t)
        if not dup:
            merged.append((cx2, cy2, text2, conf2))
    return merged


# ─────────────────────────────────────────────────────────────────────────────
#  עזר
# ─────────────────────────────────────────────────────────────────────────────

def _find_numbers(text: str) -> list:
    text = text.replace(',', '.')   # תיקון: 402,32 → 402.32
    nums = []
    for m in re.finditer(r'\d+\.\d+', text):
        try: nums.append(float(m.group()))
        except: pass
    if not nums:
        for m in re.finditer(r'\d{3,}', text):
            try: nums.append(float(m.group()))
            except: pass
    return nums


def _is_coord(v: float) -> bool:
    return (50 <= v <= 10_000) or (100_000 <= v <= 900_000)


def _is_valid_gemini_coord(v: float) -> bool:
    """פורמט תקין: 3 ספרות עשרוני (100-999) או 6 ספרות עשרוני (100000-999999)"""
    return (100.0 <= v < 1000.0) or (100_000.0 <= v < 1_000_000.0)


def _clean_name(t: str) -> str:
    return re.sub(r'[^0-9A-Za-z]', '', t.strip())


def _is_name(t: str) -> bool:
    n = _clean_name(t)
    return bool(n and re.match(r'^[0-9]{1,4}[A-Za-z]{0,2}$', n))


def _to_rows(items: list, tol: int = 22) -> dict:
    rows = defaultdict(list)
    for cx, cy, text, conf in items:
        key = round(cy / tol) * tol
        rows[key].append((cx, text))
    return {k: sorted(v) for k, v in sorted(rows.items())}


def _is_valid(name: str, y: float, x: float) -> bool:
    nn = re.sub(r'[^0-9]', '', name)
    if len(nn) > 4: return False
    n = float(nn) if nn else 0
    if x < 100 or y < 100: return False
    if 4000 < y < 100_000: return False
    if n > 0 and abs(x - n) < max(5, n * 0.02): return False
    if n > 0 and abs(y - n) < max(5, n * 0.02): return False
    if abs(y - x) < 2: return False
    return True

# ─────────────────────────────────────────────────────────────────────────────
#  סוג עמוד
# ─────────────────────────────────────────────────────────────────────────────

def _detect_page_type(items: list, img_w: int) -> str:
    """
    מזהה סוג עמוד לפי:
    1. מצולע: יש Sn/Cs, קואורדינטות רק בימין
    2. שטחים: הרבה שורות עם קואורדינטות בחלק השמאלי (14-55%)
    3. בינים: קואורדינטות ב-61-83%
    """
    texts = ' '.join(t for _, _, t, _ in items).lower()

    # מצולע — SN ו-CS (עם whitelist אותיות גדולות)
    if ('SN' in texts.upper() and 'CS' in texts.upper()) or \
       ('sn' in texts and 'cs' in texts):
        return 'matzola'

    # ספור שורות עם קואורדינטות בחלק השמאלי-אמצעי (14%-55%)
    rows_with_left_coord = set()
    for cx, cy, text, _ in items:
        pct = cx / img_w
        if 0.14 <= pct <= 0.55:
            nums = _find_numbers(text)
            for v in nums:
                if _is_coord(v) and v > 100:
                    rows_with_left_coord.add(round(cy / 25) * 25)

    # שטחים: יותר מ-3 שורות שונות עם קואורדינטות בשמאל
    if len(rows_with_left_coord) >= 3:
        return 'shtachim'

    return 'beinim'

# ─────────────────────────────────────────────────────────────────────────────
#  חלץ לפי סוג
# ─────────────────────────────────────────────────────────────────────────────

def _extract_matzola(items: list, img_w: int, arr) -> list:
    """
    חשוב מצולע — גישה חדשה: מאחד Y ו-X לפי שם הנקודה על פני כמה שורות.
    Y @ 62-81%, X @ 81-92%, שמות < 14% ו > 92%.
    """
    from PIL import Image as _PIL
    # OCR נוסף על גזרת YX עם whitelist ספרות
    img_pil = _PIL.fromarray(arr)
    h = arr.shape[0]
    y0, y1 = int(img_w * 0.60), int(img_w * 0.93)
    strip = img_pil.crop((y0, 0, y1, h))
    yx_raw = _ocr_strip(strip, psm=11,
                        extra='-c tessedit_char_whitelist=0123456789.')
    yx = [(cx + y0, cy, t, conf) for cx, cy, t, conf in yx_raw]
    all_items = list(items) + yx

    Y_S, Y_E = int(img_w * 0.62), int(img_w * 0.81)
    X_S, X_E = int(img_w * 0.81), int(img_w * 0.95)
    LN, RN   = int(img_w * 0.14), int(img_w * 0.92)

    # שלב 1: אסוף שמות, Y, X לפי מיקום y (±40px tolerance)
    # כל פריט: (row_y, zone, value_or_name)
    name_at = {}   # row_y → שם נקודה
    y_at    = {}   # row_y → Y value
    x_at    = {}   # row_y → X value

    for cx, cy, text, conf in all_items:
        ry = round(cy / 25) * 25   # עיגול ל-25px
        nums = _find_numbers(text)

        if cx <= LN and _is_name(text):
            name_at[ry] = _clean_name(text)
        if cx >= RN and _is_name(text):
            name_at[ry] = _clean_name(text)

        for v in nums:
            if Y_S <= cx < Y_E and _is_coord(v):
                y_at[ry] = v
            elif X_S <= cx < X_E and _is_coord(v):
                x_at[ry] = v

    # שלב 2: חפש התאמות שם+Y+X בחלון ±100px
    TOL = 100
    points = []
    used_names = set()

    for ry, name in sorted(name_at.items()):
        if name in used_names:
            continue
        # חפש Y ו-X בחלון
        y_val = next((y_at[r] for r in y_at
                      if abs(r - ry) <= TOL), None)
        x_val = next((x_at[r] for r in x_at
                      if abs(r - ry) <= TOL), None)

        if y_val and x_val and y_val >= 100:
            used_names.add(name)
            points.append({'שם נקודה': name,
                           'Y': round(y_val, 3),
                           'X': round(x_val, 3)})

    return points


def _extract_beinim(items: list, img_w: int) -> list:
    """
    חשוב קואורדינטות של נקודות הבינים
    עמודת A/Y: 61-72%, A/X: 73-82%
    שמות: < 8% (שמאל) ו > 93% (ימין)
    """
    Y_S, Y_E = int(img_w * 0.61), int(img_w * 0.72)
    X_S, X_E = int(img_w * 0.73), int(img_w * 0.83)
    LN       = int(img_w * 0.10)
    RN       = int(img_w * 0.93)

    rows = _to_rows(items)
    points = []
    for row_y, row_items in rows.items():
        y_vals, x_vals, l_names, r_names = [], [], [], []
        for cx, text in row_items:
            nums = _find_numbers(text)
            if cx <= LN and _is_name(text):
                l_names.append(_clean_name(text))
            if cx >= RN and _is_name(text):
                r_names.append(_clean_name(text))
            for v in nums:
                if Y_S <= cx < Y_E and _is_coord(v):
                    y_vals.append(v)
                elif X_S <= cx < X_E and _is_coord(v):
                    x_vals.append(v)
        name = (r_names or l_names or [None])[0]
        if name and y_vals and x_vals:
            points.append({'שם נקודה': name,
                           'Y': round(y_vals[0], 3),
                           'X': round(x_vals[0], 3)})
    return points


def _extract_shtachim(items: list, img_w: int) -> list:
    """
    חשוב שטחים — כל הדף.
    שמות: 5-14% (שמאל) ו 51-63% (ימין)
    קואורדינטות: כל מספר עשרוני > 100 בכל הדף
    אחוד: לכל שם — שתי קואורדינטות קרובות ביותר
    """
    LN_L  = int(img_w * 0.05); LN_R  = int(img_w * 0.14)
    RN_L  = int(img_w * 0.50); RN_R  = int(img_w * 0.64)

    # אסוף כל הקואורדינטות עם מיקום
    all_coords = []   # (cy, cx, value)
    l_names_at = {}   # cy_rounded → name
    r_names_at = {}

    for cx, cy, text, conf in items:
        ry = round(cy / 20) * 20
        nums = _find_numbers(text)

        if LN_L <= cx < LN_R and _is_name(text):
            l_names_at[ry] = _clean_name(text)
        if RN_L <= cx < RN_R and _is_name(text):
            r_names_at[ry] = _clean_name(text)

        for v in nums:
            # קואורדינטה: מספר עשרוני > 100
            if _is_coord(v) and v > 100 and '.' in text:
                all_coords.append((cy, cx, v))

    points = []
    used = set()
    TOL = 80  # ±80px לחיפוש קואורדינטות

    def _nearest_two(target_cy, section_cx_min, section_cx_max):
        """מוצא 2 קואורדינטות קרובות לcy בתחום cx"""
        cands = [(cy2, cx2, v) for cy2, cx2, v in all_coords
                 if abs(cy2 - target_cy) <= TOL
                 and section_cx_min <= cx2 < section_cx_max]
        cands.sort(key=lambda z: abs(z[0] - target_cy))
        vals = [v for _, _, v in cands]
        return (vals[0], vals[1]) if len(vals) >= 2 else (None, None)

    for ry, name in sorted(l_names_at.items()):
        if name in used: continue
        y, x = _nearest_two(ry, int(img_w*0.12), int(img_w*0.58))
        if y and x:
            used.add(name)
            points.append({'שם נקודה': name, 'Y': round(y,3), 'X': round(x,3)})

    for ry, name in sorted(r_names_at.items()):
        if name in used: continue
        y, x = _nearest_two(ry, int(img_w*0.61), img_w)
        if y and x:
            used.add(name)
            points.append({'שם נקודה': name, 'Y': round(y,3), 'X': round(x,3)})

    return points

# ─────────────────────────────────────────────────────────────────────────────
#  עיבוד עמוד
# ─────────────────────────────────────────────────────────────────────────────

def _process_page(arr: np.ndarray, use_combined: bool = False) -> list:
    # בחר מנוע OCR
    items = _ocr_combined(arr) if use_combined else _ocr_full(arr)
    img_w = arr.shape[1]
    page_type = _detect_page_type(items, img_w)

    if page_type == 'matzola':
        pts = _extract_matzola(items, img_w, arr)
    elif page_type == 'beinim':
        pts = _extract_beinim(items, img_w)
    elif page_type == 'shtachim':
        pts = _extract_sztachim(items, img_w)
    else:
        pts = _extract_matzola(items, img_w, arr)

    return pts


def _extract_sztachim(items, img_w):
    """alias"""
    return _extract_sztachim_inner(items, img_w)


def _extract_sztachim_inner(items, img_w):
    return _extract_sztachim_full(items, img_w)


def _extract_sztachim_full(items, img_w):
    return _extract_shtachim(items, img_w)

# ─────────────────────────────────────────────────────────────────────────────
#  ממשק ציבורי
# ─────────────────────────────────────────────────────────────────────────────

def extract_from_tif(
    file_bytes: bytes,
    progress_cb=None,
    max_pages: int = 0,
    reference_df: pd.DataFrame = None,
    use_combined: bool = False,
) -> pd.DataFrame:
    """
    use_combined=True  → Tesseract + EasyOCR (מדויק יותר, איטי יותר)
    use_combined=False → Tesseract בלבד (מהיר)
    """
    if reference_df is not None and len(reference_df) > 0:
        return extract_with_csv_reference(file_bytes, reference_df, progress_cb)

    img = Image.open(io.BytesIO(file_bytes))
    n_pages = getattr(img, 'n_frames', 1)
    if max_pages and max_pages < n_pages:
        n_pages = max_pages

    all_points = []
    page_order = list(range(n_pages - 1, -1, -1))
    for idx, page_num in enumerate(page_order):
        img.seek(page_num)
        if not _has_content(img):
            if progress_cb: progress_cb(idx + 1, n_pages)
            continue
        arr = _prepare(img)
        try:
            pts = _process_page(arr, use_combined=use_combined)
            all_points.extend(pts)
        except Exception as e:
            print(f"Page {page_num+1}: {e}")
        if progress_cb:
            progress_cb(idx + 1, n_pages)

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X'])
    df = df[df.apply(lambda r: _is_valid(str(r['שם נקודה']), r['Y'], r['X']), axis=1)]
    return df.drop_duplicates('שם נקודה').reset_index(drop=True)


def extract_with_csv_reference(
    tif_bytes: bytes,
    csv_df: pd.DataFrame,
    progress_cb=None,
    tolerance: float = 1.5,
) -> pd.DataFrame:
    known_Y = {float(v): name for name, v in zip(csv_df['שם נקודה'], csv_df['Y'])}
    known_X = {float(v): name for name, v in zip(csv_df['שם נקודה'], csv_df['X'])}

    img = Image.open(io.BytesIO(tif_bytes))
    n_pages = getattr(img, 'n_frames', 1)
    found: dict = {}

    for page_num in range(n_pages):
        img.seek(page_num)
        if not _has_content(img):
            if progress_cb: progress_cb(page_num + 1, n_pages)
            continue
        arr = _prepare(img)
        items = _ocr_full(arr)

        for cx, cy, text, conf in items:
            for v in _find_numbers(text):
                for truth_y, pt in known_Y.items():
                    # בדיקה רגילה + בדיקת suffix (OCR קרא 644.32 במקום 151644.32)
                    if abs(v - truth_y) <= tolerance or \
                       abs(truth_y % 1000 - v) <= tolerance:
                        found.setdefault(pt, {})['Y'] = truth_y
                for truth_x, pt in known_X.items():
                    if abs(v - truth_x) <= tolerance or \
                       abs(truth_x % 1000 - v) <= tolerance:
                        found.setdefault(pt, {})['X'] = truth_x

        if progress_cb: progress_cb(page_num + 1, n_pages)

    rows = [{'שם נקודה': n, 'Y': v['Y'], 'X': v['X'], 'מקור': 'OCR ✓'}
            for n, v in found.items() if 'Y' in v and 'X' in v]

    df_found = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['שם נקודה','Y','X','מקור'])
    found_names = set(df_found['שם נקודה']) if len(df_found) else set()
    missing = csv_df[~csv_df['שם נקודה'].isin(found_names)].copy()
    missing['מקור'] = 'CSV'

    return pd.concat([df_found, missing[['שם נקודה','Y','X','מקור']]],
                     ignore_index=True).reset_index(drop=True)


def extract_with_gemini(
    tif_bytes: bytes,
    api_key: str,
    progress_cb=None,
) -> pd.DataFrame:
    """
    שולח 5 דפים במקביל ל-Gemini, מחזיר קואורדינטות בסדר עמודים.
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

    # טען כל הדפים לזיכרון (PIL לא thread-safe ל-seek)
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
            return p, []

        t0 = time.time()
        offset = t0 - t_global
        print(f"P{p+1}: START (+{offset:.1f}s, {len(img_b64)//1024}KB)")

        payload = {"contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": PROMPT}
        ]}]}

        pts = []
        for attempt in range(2):   # max 2 attempts
            try:
                resp = requests.post(API_URL, json=payload, headers=HDR, timeout=70)
                if resp.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"P{p+1}: 429, wait {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    print(f"P{p+1}: HTTP {resp.status_code}")
                    break   # don't retry on non-429 errors
                raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
                # נסה לפרסר כ-dict (פורמט חדש) או כ-list (פורמט ישן)
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
                        sug = TYPE_HE.get(pt, '')  # ריק אם לא סווג
                        pts.append({'שם נקודה': name, 'Y': y, 'X': x,
                                    'סוג': sug})
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
    result_meta = {}  # p -> has_headers

    # ── עובר ראשון ────────────────────────────────────────────────────────────
    for batch_start in range(0, n_pages, BATCH):
        batch = list(range(batch_start, min(batch_start + BATCH, n_pages)))
        bt0 = time.time()
        print(f"\n-- Batch {batch_start//BATCH+1} -- pages {[p+1 for p in batch]}")
        with ThreadPoolExecutor(max_workers=BATCH) as pool:
            futures = {pool.submit(_send_page, p): p for p in batch}
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

    # ── Adaptive retry: דפים גדולים עם 0 נקודות ────────────────────────────
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

    # ── Continuation pass: דפי המשך ללא כותרות שעדיין ריקים ────────────────
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

    # אסוף בסדר עמודים
    all_points = [pt for p in range(n_pages) for pt in results.get(p, [])]
    print(f"Done: {len(all_points)} total points")

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X'])

    # ── תיקון סדר Y/X אוטומטי לכל מערכת קואורדינטות ──────────────────────────
    y_med = df['Y'].median()
    x_med = df['X'].median()

    # בדיקה גלובלית: אם Y גדול מ-X ב-50% → כנראה מוחלף
    if y_med > x_med * 1.5:
        df = df.rename(columns={'Y': '_tmp', 'X': 'Y'}).rename(columns={'_tmp': 'X'})
        y_med, x_med = x_med, y_med

    # בדיקה ברמת שורה: לרשת ישנה/ITM (X > 400,000)
    # Y אמור להיות קטן מ-X — אחרת החלף
    if x_med > 400_000:
        mask = df['Y'] > df['X']
        if mask.sum() > 0:
            df.loc[mask, ['Y', 'X']] = df.loc[mask, ['X', 'Y']].values

    # Voting dedup — מוצא הקבוצה הנפוצה ביותר, שומר ערך מקורי מלא
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
            entry['סוג'] = row.get('סוג', 'חדשה')
        best.append(entry)
    return pd.DataFrame(best)


def spatial_match_to_reference(
    extracted_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """
    מתאים קואורדינטות מחולצות לנקודות ייחוס לפי מרחק מרחבי.
    מתקן drift: שם שגוי שקיבל קואורדינטה נכונה → מקבל את השם הנכון.

    extracted_df: [שם נקודה, Y, X] — קואורדינטות מקומיות או מלאות
    reference_df: [שם נקודה, Y, X] — קואורדינטות מלאות (ייחוס)
    threshold:    מרחק מקסימלי (מטר) להתאמה
    """
    if extracted_df.empty or reference_df.empty:
        return extracted_df

    ref = reference_df.copy()
    ref_name_col = [c for c in ref.columns if c not in ['Y', 'X']][0]
    ref = ref.rename(columns={ref_name_col: 'name_ref',
                               'Y': 'Y_ref', 'X': 'X_ref'})
    ref['Y_ref'] = pd.to_numeric(ref['Y_ref'], errors='coerce')
    ref['X_ref'] = pd.to_numeric(ref['X_ref'], errors='coerce')
    ref = ref.dropna().reset_index(drop=True)

    ext = extracted_df.copy()
    ext_name_col = [c for c in ext.columns if c not in ['Y', 'X']][0]
    ext['Y'] = pd.to_numeric(ext['Y'], errors='coerce')
    ext['X'] = pd.to_numeric(ext['X'], errors='coerce')
    ext = ext.dropna(subset=['Y', 'X']).reset_index(drop=True)

    # זיהוי scale: קואורדינטות מקומיות (< 10000) מול מלאות
    y_med_ext = ext['Y'].median()
    x_med_ext = ext['X'].median()
    y_med_ref = ref['Y_ref'].median()
    x_med_ref = ref['X_ref'].median()

    if y_med_ext < 10000 and y_med_ref > 10000:
        y_offset = round(y_med_ref / 1000) * 1000 - round(y_med_ext / 1000) * 1000
        x_offset = round(x_med_ref / 1000) * 1000 - round(x_med_ext / 1000) * 1000
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
            rows.append({
                'שם נקודה': ref_names[idx],
                'Y': float(ref_y[idx]),
                'X': float(ref_x[idx]),
            })
        else:
            rows.append({
                'שם נקודה': row[ext_name_col],
                'Y': row['Y'],
                'X': row['X'],
            })

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
                        if _is_coord(y) and _is_coord(x) and name:
                            all_points.append({'שם נקודה': name, 'Y': y, 'X': x})
                    except: continue
    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])
    return pd.DataFrame(all_points).drop_duplicates('שם נקודה').reset_index(drop=True)
