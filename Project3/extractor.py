"""
extractor.py — חילוץ קואורדינטות מתיקי חישובים (TIF/PDF)
גישה: Tesseract OCR + אימות מול CSV קיים (ground-truth validation)
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

# ── הכנת תמונה ───────────────────────────────────────────────────────────────

def _prepare(img: Image.Image) -> np.ndarray:
    """גווני אפור + ניגודיות + הגדלה ל-1600px"""
    import PIL.ImageEnhance as IE
    img = img.convert('L')
    w, h = img.size
    target = 1600
    if w < target:
        img = img.resize((target, int(h * target / w)), Image.LANCZOS)
    img = IE.Contrast(img).enhance(2.0)
    img = IE.Sharpness(img).enhance(2.0)
    return np.array(img.convert('RGB'))


def _has_content(img: Image.Image) -> bool:
    arr = np.array(img.convert('L'))
    black = (arr < 128).mean()
    return 0.02 <= black <= 0.75

# ── OCR ──────────────────────────────────────────────────────────────────────

def _ocr(img_array: np.ndarray) -> list:
    """מחזיר [(cx, cy, text, conf), ...]"""
    from PIL import Image as _PIL
    img = _PIL.fromarray(img_array)
    data = pytesseract.image_to_data(
        img, output_type=pytesseract.Output.DICT,
        lang='eng', config=r'--oem 1 --psm 11',
    )
    items = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if not text or conf < 15:
            continue
        cx = data['left'][i] + data['width'][i] // 2
        cy = data['top'][i] + data['height'][i] // 2
        items.append((cx, cy, text, conf / 100.0))
    return items

# ── עזר ──────────────────────────────────────────────────────────────────────

def _find_numbers(text: str) -> list:
    """מחזיר את כל המספרים העשרוניים בטקסט"""
    parts = []
    for m in re.finditer(r'\d+\.\d+', text):
        try:
            parts.append(float(m.group()))
        except ValueError:
            pass
    if not parts:
        for m in re.finditer(r'\d{2,}', text):
            try:
                parts.append(float(m.group()))
            except ValueError:
                pass
    return parts


def _clean_name(text: str) -> str:
    return re.sub(r'[^0-9A-Za-z]', '', text.strip())


def _is_name(text: str) -> bool:
    t = _clean_name(text)
    return bool(t and re.match(r'^[0-9]{1,5}[A-Za-z]{0,2}$', t))


def _is_coord(v: float) -> bool:
    return (50 <= v <= 10_000) or (100_000 <= v <= 900_000)

# ── ════════════════════════════════════════════════════════════════════════ ──
#   גישה א׳ — לימוד מ-CSV (Ground-Truth Validation)
#   לכל TIF שיש לו CSV מקביל: OCR + חיפוש התאמות עם סובלנות
# ── ════════════════════════════════════════════════════════════════════════ ──

def extract_with_csv_reference(
    tif_bytes: bytes,
    csv_df: pd.DataFrame,
    progress_cb=None,
    tolerance: float = 1.5,
) -> pd.DataFrame:
    """
    חילוץ מתוחכם: מריץ OCR ומאמת מול CSV קיים.
    כל מספר שנמצא ב-OCR ומתאים (בטולרנס) לערך ב-CSV — נקלט.
    מחזיר DataFrame: שם נקודה, Y, X  עם עמודת מקור='OCR'/'CSV'.
    """
    known_Y = {float(v): name
               for name, v in zip(csv_df['שם נקודה'], csv_df['Y'])}
    known_X = {float(v): name
               for name, v in zip(csv_df['שם נקודה'], csv_df['X'])}

    img = Image.open(io.BytesIO(tif_bytes))
    n_pages = getattr(img, 'n_frames', 1)

    # מיפוי: שם נקודה → {Y: ..., X: ...}
    found: dict = {}

    for page_num in range(n_pages):
        img.seek(page_num)
        if not _has_content(img):
            if progress_cb:
                progress_cb(page_num + 1, n_pages)
            continue

        arr = _prepare(img)
        items = _ocr(arr)

        for cx, cy, text, conf in items:
            nums = _find_numbers(text)
            for v in nums:
                # בדוק התאמה ל-Y
                for truth_y, pt_name in known_Y.items():
                    if abs(v - truth_y) <= tolerance:
                        if pt_name not in found:
                            found[pt_name] = {}
                        found[pt_name]['Y'] = truth_y
                        found[pt_name].setdefault('name', pt_name)
                        break
                # בדוק התאמה ל-X
                for truth_x, pt_name in known_X.items():
                    if abs(v - truth_x) <= tolerance:
                        if pt_name not in found:
                            found[pt_name] = {}
                        found[pt_name]['X'] = truth_x
                        found[pt_name].setdefault('name', pt_name)
                        break

        if progress_cb:
            progress_cb(page_num + 1, n_pages)

    # בנה תוצאות — נקודות שנמצאו Y וגם X
    rows = []
    for name, vals in found.items():
        if 'Y' in vals and 'X' in vals:
            rows.append({'שם נקודה': name, 'Y': vals['Y'], 'X': vals['X']})

    # כל נקודה שלא נמצאה ב-OCR — הוסף מה-CSV (בסימון מקור)
    found_names = {r['שם נקודה'] for r in rows}
    missing = csv_df[~csv_df['שם נקודה'].isin(found_names)].copy()

    df_found   = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['שם נקודה','Y','X'])
    df_found['מקור'] = 'OCR ✓'
    missing['מקור']  = 'CSV (לא נמצא ב-OCR)'

    result = pd.concat([df_found, missing[['שם נקודה','Y','X','מקור']]], ignore_index=True)
    return result.sort_values('שם נקודה').reset_index(drop=True)


# ── ════════════════════════════════════════════════════════════════════════ ──
#   גישה ב׳ — OCR בלבד (לקבצים חדשים ללא CSV)
#   אותם אחוזי עמודה שנלמדו מהדוגמאות: Y=69%, X=83%
# ── ════════════════════════════════════════════════════════════════════════ ──

def _to_rows(items: list, tol: int = 22) -> dict:
    rows = defaultdict(list)
    for cx, cy, text, conf in items:
        key = round(cy / tol) * tol
        rows[key].append((cx, text))
    return {k: sorted(v) for k, v in sorted(rows.items())}


def _extract_page_ocr_only(items: list, img_w: int) -> list:
    """
    מאחוזים שנלמדו: Y=67-82%, X=80-97%
    שמות נקודה: <14% (שמאל) או >93% (ימין)
    """
    Y_START = int(img_w * 0.67)
    Y_END   = int(img_w * 0.82)
    X_START = int(img_w * 0.80)
    X_END   = int(img_w * 0.97)
    L_NAME  = int(img_w * 0.14)
    R_NAME  = int(img_w * 0.93)

    rows = _to_rows(items)
    points = []

    for row_y, row_items in rows.items():
        y_vals, x_vals, l_names, r_names = [], [], [], []

        for cx, text in row_items:
            nums = _find_numbers(text)

            if cx <= L_NAME and _is_name(text):
                l_names.append(_clean_name(text))
            if cx >= R_NAME and _is_name(text):
                r_names.append(_clean_name(text))

            for v in nums:
                if Y_START <= cx < Y_END and _is_coord(v):
                    y_vals.append(v)
                elif X_START <= cx < X_END and _is_coord(v):
                    x_vals.append(v)

        name = (r_names or l_names or [None])[0]
        if name and y_vals and x_vals and y_vals[0] >= 80:
            points.append({'שם נקודה': name,
                           'Y': round(y_vals[0], 3),
                           'X': round(x_vals[0], 3)})
    return points


def extract_from_tif(
    file_bytes: bytes,
    progress_cb=None,
    max_pages: int = 0,
    reference_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    ממשק ראשי.
    אם reference_df סופק (CSV קיים) — משתמש בגישת האימות המדויקת.
    אחרת — OCR בלבד.
    """
    if reference_df is not None and len(reference_df) > 0:
        return extract_with_csv_reference(
            file_bytes, reference_df,
            progress_cb=progress_cb,
        )

    # OCR בלבד
    img = Image.open(io.BytesIO(file_bytes))
    n_pages = getattr(img, 'n_frames', 1)
    if max_pages and max_pages < n_pages:
        n_pages = max_pages

    all_points = []
    for page_num in range(n_pages):
        img.seek(page_num)
        if not _has_content(img):
            if progress_cb:
                progress_cb(page_num + 1, n_pages)
            continue
        arr = _prepare(img)
        try:
            pts = _extract_page_ocr_only(_ocr(arr), arr.shape[1])
            all_points.extend(pts)
        except Exception as e:
            print(f"Page {page_num+1}: {e}")
        if progress_cb:
            progress_cb(page_num + 1, n_pages)

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    return df.dropna(subset=['Y','X']).drop_duplicates('שם נקודה').reset_index(drop=True)


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
                    if not row or len(row) < 3:
                        continue
                    name = str(row[0] or '').strip()
                    try:
                        y = float(str(row[1]).replace(',', '.'))
                        x = float(str(row[2]).replace(',', '.'))
                        if _is_coord(y) and _is_coord(x) and name:
                            all_points.append({'שם נקודה': name, 'Y': y, 'X': x})
                    except ValueError:
                        continue
    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])
    return pd.DataFrame(all_points).drop_duplicates('שם נקודה').reset_index(drop=True)
