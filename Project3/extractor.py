"""
extractor.py — חילוץ קואורדינטות מתיקי חישובים (TIF/PDF) באמצעות EasyOCR
"""

import re
import io
import numpy as np
import pandas as pd
from PIL import Image
from collections import defaultdict

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        from paddleocr import PaddleOCR
        _reader = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=False,
            show_log=False,
        )
    return _reader


# ── ניקוי טקסט OCR ──────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """תיקון שגיאות OCR נפוצות במספרים"""
    text = text.strip()
    text = text.replace('O', '0').replace('o', '0')
    text = text.replace('l', '1').replace('I', '1').replace('|', '1')
    text = text.replace(' ', '').replace(',', '.')
    text = re.sub(r'[^0-9.\-+]', '', text)
    return text


def _parse_number(text: str):
    """מחזיר float אם הטקסט מכיל מספר עשרוני תקין, אחרת None"""
    s = _clean(text)
    try:
        v = float(s)
        return v if v != 0 else None
    except ValueError:
        return None


def _is_coord(val: float) -> bool:
    """בודק אם הערך יכול להיות קואורדינטה (מקומי או ITM)"""
    # מערכת מקומית: 50 – 10000
    if 50 <= val <= 10000:
        return True
    # ITM מלא: 100000 – 900000
    if 100000 <= val <= 900000:
        return True
    return False


def _is_point_name(text: str) -> bool:
    """בודק אם הטקסט מכיל שם נקודה (מספר עם אות אופציונלית)"""
    t = text.strip()
    return bool(re.match(r'^[0-9]{1,5}[A-Za-z]?$', t) or re.match(r'^[A-Z]$', t))


# ── ניתוח עמוד OCR ───────────────────────────────────────────────────────────

def _group_rows(results, row_tol=18):
    """מקבץ תוצאות OCR לפי שורות (לפי מיקום y)"""
    rows = defaultdict(list)
    for bbox, text, conf in results:
        if conf < 0.35:
            continue
        cy = int(sum(p[1] for p in bbox) / 4)
        cx = int(sum(p[0] for p in bbox) / 4)
        key = round(cy / row_tol) * row_tol
        rows[key].append((cx, cy, text, conf))
    return {k: sorted(v, key=lambda x: x[0]) for k, v in sorted(rows.items())}


def _combine_split_coord(raw_pairs: list):
    """
    מאחד מספרים שפוצלו ע"י OCR: (339, 23) → 339.23
    raw_pairs: רשימת (x_pos, value) ממוינת לפי x
    """
    if not raw_pairs:
        return []
    raw_pairs = sorted(raw_pairs, key=lambda z: z[0])

    # מספר יחיד גדול — החזר אותו
    large = [v for _, v in raw_pairs if _is_coord(v)]
    if len(large) == 1:
        return large

    # שני מספרים סמוכים — נסה לחבר כ-integer.decimal
    if len(raw_pairs) >= 2:
        (x1, v1), (x2, v2) = raw_pairs[0], raw_pairs[1]
        if x2 - x1 < 160 and v1 >= 50:
            try:
                combined = float(f"{int(v1)}.{int(v2)}")
                if _is_coord(combined):
                    return [combined]
            except Exception:
                pass

    return large or [v for _, v in raw_pairs if v >= 10]


def _extract_from_matzola(rows, img_w):
    """
    חשוב מצולע — עמודות (שמאל→ימין):
      שם | זווית | אזימוט | אורך | sn/cs | Y | X | שם
    אחוזים (מורחבים מעט):
      שם שמאל : 0–15%
      Y        : 63–82%
      X        : 82–99%
      שם ימין : 94–110%  (+ שוליים לחריגות OCR)
    """
    L_NAME = (0,             int(img_w * 0.15))
    Y_ZONE = (int(img_w * 0.63), int(img_w * 0.82))
    X_ZONE = (int(img_w * 0.82), int(img_w * 0.99))
    R_NAME = (int(img_w * 0.94), img_w + 60)   # +60 לשוליות OCR

    points = []

    for row_y, items in rows.items():
        y_vals, x_raw, l_names, r_names = [], [], [], []

        for cx, cy, text, conf in items:
            num = _parse_number(text)

            if cx < L_NAME[1]:
                if _is_point_name(text):
                    l_names.append(text.strip())

            if Y_ZONE[0] <= cx < Y_ZONE[1]:
                if num and _is_coord(num):
                    y_vals.append(num)

            if X_ZONE[0] <= cx < X_ZONE[1]:
                if num is not None and num >= 10:
                    x_raw.append((cx, num))

            if cx >= R_NAME[0]:
                if _is_point_name(text):
                    r_names.append(text.strip())

        x_vals = _combine_split_coord(x_raw)
        name = (r_names or l_names or [None])[0]

        if name and y_vals and x_vals:
            # סנן שורות תיקון: Y קטן מ-50 = דלתא, לא קואורדינטה
            if y_vals[0] >= 50:
                points.append({
                    'שם נקודה': name,
                    'Y': round(y_vals[0], 3),
                    'X': round(x_vals[0], 3),
                })

    return points


def _extract_generic(rows, img_w):
    """
    חילוץ גנרי — מחפש שורות עם שם נקודה + שתי קואורדינטות בחצי ימני
    """
    RIGHT = int(img_w * 0.52)
    points = []

    for row_y, items in rows.items():
        names, coord_raw = [], []

        for cx, cy, text, conf in items:
            if _is_point_name(text):
                names.append((cx, text.strip()))
            num = _parse_number(text)
            if num and num >= 10 and cx > RIGHT:
                coord_raw.append((cx, num))

        coord_raw.sort(key=lambda z: z[0])
        coords = [v for _, v in coord_raw if _is_coord(v)]

        if len(coords) >= 2 and names:
            name = sorted(names, key=lambda z: z[0])[0][1]
            if coords[0] >= 50:
                points.append({
                    'שם נקודה': name,
                    'Y': round(coords[0], 3),
                    'X': round(coords[1], 3),
                })

    return points


def _is_matzola_page(rows) -> bool:
    """מזהה אם העמוד הוא חשוב מצולע לפי מילות מפתח"""
    keywords = {'sn', 'cs', 'a', 'matzola', 'מצולע'}
    for items in rows.values():
        for _, _, text, _ in items:
            if text.strip().lower() in keywords:
                return True
    return False


# ── שיפורי מהירות ────────────────────────────────────────────────────────────

# רזולוציה מקסימלית לפני OCR — 1200px שומר על קריאות כתב יד
MAX_WIDTH = 1200

def _resize_for_ocr(img: Image.Image) -> np.ndarray:
    """מקטין תמונה אם רחבה מדי ומשפר ניגודיות"""
    import PIL.ImageEnhance as IE
    # המרה ל-RGB לפני כל עיבוד (TIF בינארי הוא mode='1')
    img = img.convert('RGB')
    w, h = img.size
    if w > MAX_WIDTH:
        ratio = MAX_WIDTH / w
        img = img.resize((MAX_WIDTH, int(h * ratio)), Image.LANCZOS)
    # שיפור ניגודיות לכתב יד סרוק
    img = IE.Contrast(img).enhance(1.5)
    img = IE.Sharpness(img).enhance(1.3)
    return np.array(img)


def _has_enough_text(img: Image.Image, min_density=0.03, max_density=0.6) -> bool:
    """
    בודק צפיפות פיקסלים שחורים בתמונה בינארית.
    עמוד ריק / שער: צפיפות נמוכה → דלג.
    עמוד שחור לחלוטין (שגיאה): צפיפות גבוהה → דלג.
    """
    arr = np.array(img.convert('L'))   # גווני אפור
    black = (arr < 128).mean()
    return min_density <= black <= max_density


# ── עיבוד עמוד בודד ──────────────────────────────────────────────────────────

def _paddle_to_standard(paddle_result) -> list:
    """ממיר פלט PaddleOCR לפורמט אחיד: [(bbox, text, conf), ...]"""
    items = []
    if not paddle_result or not paddle_result[0]:
        return items
    for line in paddle_result[0]:
        if line is None:
            continue
        bbox, (text, conf) = line
        items.append((bbox, text, conf))
    return items


def _process_page(img_array) -> list:
    reader = _get_reader()
    raw = reader.ocr(img_array, cls=True)
    results = _paddle_to_standard(raw)
    img_w = img_array.shape[1]
    rows = _group_rows(results)

    if _is_matzola_page(rows):
        return _extract_from_matzola(rows, img_w)
    else:
        return _extract_generic(rows, img_w)


# ── ממשק ציבורי ───────────────────────────────────────────────────────────────

def extract_from_tif(file_bytes: bytes, progress_cb=None) -> pd.DataFrame:
    """
    מקבל bytes של קובץ TIF רב-עמודי,
    מחזיר DataFrame עם עמודות: שם נקודה, Y, X
    שיפורי מהירות: דילוג עמודים ריקים + הקטנת רזולוציה
    """
    img = Image.open(io.BytesIO(file_bytes))
    n_pages = getattr(img, 'n_frames', 1)

    all_points = []
    skipped = 0

    for page_num in range(n_pages):
        img.seek(page_num)

        # שיפור 1 — דלג על עמודים ריקים/שערים
        if not _has_enough_text(img):
            skipped += 1
            if progress_cb:
                progress_cb(page_num + 1, n_pages)
            continue

        # שיפור 2 — הקטן רזולוציה לפני OCR
        arr = _resize_for_ocr(img)

        try:
            pts = _process_page(arr)
            all_points.extend(pts)
        except Exception:
            pass

        if progress_cb:
            progress_cb(page_num + 1, n_pages)

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points)
    df = df.drop_duplicates(subset=['שם נקודה'])
    df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
    df['X'] = pd.to_numeric(df['X'], errors='coerce')
    df = df.dropna(subset=['Y', 'X']).reset_index(drop=True)
    return df


def extract_from_pdf(file_bytes: bytes) -> pd.DataFrame:
    """
    מקבל bytes של קובץ PDF,
    מחלץ קואורדינטות מטקסט ישיר (ללא OCR)
    """
    try:
        import pdfplumber
    except ImportError:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    all_points = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    name = str(row[0]).strip() if row[0] else ''
                    y_str = str(row[1]).strip() if row[1] else ''
                    x_str = str(row[2]).strip() if row[2] else ''
                    try:
                        y = float(y_str.replace(',', '.'))
                        x = float(x_str.replace(',', '.'))
                        if _is_coord(y) and _is_coord(x) and name:
                            all_points.append({'שם נקודה': name, 'Y': y, 'X': x})
                    except ValueError:
                        continue

    if not all_points:
        return pd.DataFrame(columns=['שם נקודה', 'Y', 'X'])

    df = pd.DataFrame(all_points).drop_duplicates(subset=['שם נקודה'])
    return df.reset_index(drop=True)
