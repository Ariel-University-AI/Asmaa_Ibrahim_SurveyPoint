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
    חילוץ קואורדינטות באמצעות Gemini Vision — דיוק גבוה על כתב יד.
    מודל: gemini-1.5-flash (חינם, 15 בקשות/דקה)
    """
    from google import genai
    import json, time

    # נסה ל-v1alpha שתומך ביותר מודלים
    from google.genai import types as _t
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1alpha'},
    )
    GEMINI_MODEL = "gemini-2.0-flash-exp"

    PROMPT = """זהו עמוד מתיק חישובים הנדסי של מודד מוסמך.
חלץ את כל הקואורדינטות מהטבלה.

חפש בכל סוגי הטבלאות:
- חשוב מצולע (traverse): עמודות Y ו-X בצד ימין
- חשוב קואורדינטות (נקודות בינים): עמודות A/Y ו-A/X
- חשוב שטחים (area): טבלה עם מספר נקודה, Y, X

החזר JSON בלבד, ללא טקסט נוסף:
[{"name": "שם_נקודה", "Y": 123.45, "X": 678.90}, ...]

אם אין קואורדינטות בדף — החזר: []"""

    img = Image.open(io.BytesIO(tif_bytes))
    n_pages = getattr(img, 'n_frames', 1)
    all_points = []

    for page_num in range(n_pages - 1, -1, -1):  # מהאחרון לראשון
        img.seek(page_num)
        if not _has_content(img):
            if progress_cb: progress_cb(n_pages - page_num, n_pages)
            continue

        # המר לJPEG bytes
        buf = io.BytesIO()
        img.convert('RGB').save(buf, format='JPEG', quality=90)
        img_bytes = buf.getvalue()

        try:
            from google.genai import types as gtypes
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    gtypes.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    PROMPT,
                ],
            )
            text = response.text.strip()
            print(f"Page {page_num+1}: Gemini responded {len(text)} chars")
            # נקה markdown אם יש
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = text.strip()

            parsed = json.loads(text)
            for item in parsed:
                try:
                    name = str(item.get('name', '')).strip()
                    y = float(str(item.get('Y', 0)).replace(',', '.'))
                    x = float(str(item.get('X', 0)).replace(',', '.'))
                    if name and y and x:
                        all_points.append({'שם נקודה': name, 'Y': y, 'X': x})
                except Exception:
                    continue

        except Exception as e:
            import traceback
            err_msg = f"Page {page_num+1} error: {type(e).__name__}: {e}"
            print(err_msg)
            traceback.print_exc()
            all_points.append({'שם נקודה': f'__ERROR_P{page_num+1}',
                                'Y': -1, 'X': str(e)[:80]})

        # Gemini: 15 בקשות/דקה → המתן מעט
        time.sleep(4)

        if progress_cb:
            progress_cb(n_pages - page_num, n_pages)

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X'])
    df = df.drop_duplicates(subset=['שם נקודה']).reset_index(drop=True)
    return df


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
