"""
extractor.py — חילוץ קואורדינטות מתיקי חישובים (TIF/PDF) באמצעות Tesseract OCR
"""

import re
import io
import numpy as np
import pandas as pd
from PIL import Image
from collections import defaultdict

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── הכנת תמונה ───────────────────────────────────────────────────────────────

def _prepare(img: Image.Image) -> np.ndarray:
    """המרה לגווני אפור + שיפור ניגודיות לטסרקט"""
    import PIL.ImageEnhance as IE
    img = img.convert('L')
    w, h = img.size
    if w < 1400:
        ratio = 1400 / w
        img = img.resize((1400, int(h * ratio)), Image.LANCZOS)
    img = IE.Contrast(img).enhance(2.0)
    img = IE.Sharpness(img).enhance(2.0)
    return np.array(img.convert('RGB'))


def _has_content(img: Image.Image) -> bool:
    """בודק שהעמוד לא ריק"""
    arr = np.array(img.convert('L'))
    black = (arr < 128).mean()
    return 0.02 <= black <= 0.7

# ── OCR ──────────────────────────────────────────────────────────────────────

def _ocr(img_array: np.ndarray) -> list:
    """
    מריץ Tesseract ומחזיר: [(cx, cy, text, conf), ...]
    psm=11 = sparse text — הכי מתאים לטפסי מדידה
    """
    from PIL import Image as _PIL
    img = _PIL.fromarray(img_array)
    data = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT,
        lang='eng',
        config=r'--oem 1 --psm 11',
    )
    items = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if not text or conf < 15:
            continue
        x = data['left'][i] + data['width'][i] // 2
        y = data['top'][i] + data['height'][i] // 2
        items.append((x, y, text, conf / 100.0))
    return items

# ── ניקוי וזיהוי ─────────────────────────────────────────────────────────────

def _best_number(text: str):
    """
    מחלץ את המספר הטוב ביותר מטקסט OCR רועש.
    מחזיר float או None.
    """
    # נסה קודם כמספר שלם
    t = re.sub(r'[^0-9.]', '', text)
    try:
        v = float(t)
        return v if v > 0 else None
    except ValueError:
        pass
    # מצא את רצף הספרות הארוך ביותר עם נקודה עשרונית
    matches = re.findall(r'\d+\.\d+', text)
    if matches:
        try:
            return float(max(matches, key=len))
        except ValueError:
            pass
    # מצא רצף ספרות בלבד
    matches = re.findall(r'\d{2,}', text)
    if matches:
        try:
            return float(max(matches, key=len))
        except ValueError:
            pass
    return None


def _is_coord(v: float) -> bool:
    """בודק אם הערך בטווח קואורדינטה סבירה"""
    return (50 <= v <= 10_000) or (100_000 <= v <= 900_000)


def _clean_name(text: str) -> str:
    """מנקה שם נקודה — מסיר תווי רעש"""
    return re.sub(r'[^0-9A-Za-z]', '', text.strip())


def _is_name(text: str) -> bool:
    t = _clean_name(text)
    return bool(t and re.match(r'^[0-9]{1,5}[A-Za-z]?$', t))

# ── קיבוץ לשורות ─────────────────────────────────────────────────────────────

def _to_rows(items: list, tol: int = 22) -> dict:
    """מקבץ פריטי OCR לפי שורות (y ± tol)"""
    rows = defaultdict(list)
    for cx, cy, text, conf in items:
        key = round(cy / tol) * tol
        rows[key].append((cx, cy, text, conf))
    return {k: sorted(v) for k, v in sorted(rows.items())}

# ── חילוץ קואורדינטות ────────────────────────────────────────────────────────

def _extract_page(items: list, img_w: int) -> list:
    """
    האלגוריתם החדש:
    לכל שורה — מחפש שני מספרים > 100 בחצי הימני של העמוד
    ושם נקודה (שמאל או ימין).
    מדלג על שורות תיקון (מספרים קטנים < 100).
    """
    rows = _to_rows(items)
    points = []

    # הגדרת אזורים (אחוזים מרוחב)
    MID       = int(img_w * 0.55)   # גבול אמצע
    Y_START   = int(img_w * 0.62)   # תחילת אזור Y
    Y_END     = int(img_w * 0.83)   # סוף אזור Y
    X_START   = int(img_w * 0.83)   # תחילת אזור X
    X_END     = int(img_w * 1.02)   # סוף אזור X (מעט מחוץ לתמונה)
    NAME_LEFT = int(img_w * 0.14)   # גבול שם שמאל
    NAME_RIGHT= int(img_w * 0.93)   # תחילת שם ימין

    for row_y, row_items in rows.items():
        y_cands, x_cands, left_names, right_names = [], [], [], []

        for cx, cy, text, conf in row_items:

            # שמות נקודה
            if cx <= NAME_LEFT and _is_name(text):
                left_names.append(_clean_name(text))
            if cx >= NAME_RIGHT and _is_name(text):
                right_names.append(_clean_name(text))

            # מספרים בחצי הימני
            if cx < MID:
                continue
            num = _best_number(text)
            if num is None:
                continue

            if Y_START <= cx < Y_END and _is_coord(num):
                y_cands.append(num)
            elif X_START <= cx < X_END and _is_coord(num):
                x_cands.append(num)

        name = (right_names or left_names or [None])[0]
        if name and y_cands and x_cands:
            y_val = y_cands[0]
            x_val = x_cands[0]
            # סנן שורות תיקון: Y גדול = קואורדינטה, Y קטן = דלתא
            if y_val >= 80:
                points.append({
                    'שם נקודה': name,
                    'Y': round(y_val, 3),
                    'X': round(x_val, 3),
                })

    return points


def _process_page(img_array: np.ndarray) -> list:
    items = _ocr(img_array)
    return _extract_page(items, img_array.shape[1])

# ── ממשק ציבורי ───────────────────────────────────────────────────────────────

def extract_from_tif(file_bytes: bytes, progress_cb=None, max_pages: int = 0) -> pd.DataFrame:
    """
    מקבל bytes של TIF רב-עמודי.
    מחזיר DataFrame: שם נקודה, Y, X
    max_pages=0 → כל העמודים
    """
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
            pts = _process_page(arr)
            all_points.extend(pts)
        except Exception as e:
            print(f"Page {page_num+1} error: {e}")

        if progress_cb:
            progress_cb(page_num + 1, n_pages)

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X'])
    df = df.drop_duplicates(subset=['שם נקודה']).reset_index(drop=True)
    return df


def extract_from_pdf(file_bytes: bytes) -> pd.DataFrame:
    """חילוץ מ-PDF עם טקסט ישיר (ללא OCR)"""
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
    return pd.DataFrame(all_points).drop_duplicates(subset=['שם נקודה']).reset_index(drop=True)
