import os
import io
import zipfile
import csv
import tempfile
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
from openpyxl import load_workbook

# ── Font cache so we never load the same font+size from disk twice ──────────
_font_cache = {}

def _get_font(font_path, size):
    key = (font_path, size)
    if key not in _font_cache:
        if font_path:
            _font_cache[key] = ImageFont.truetype(font_path, size)
        else:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def _resolve_font_path(font_name):
    for candidate in [f"fonts/{font_name}.ttf", "default_font.ttf", "font.ttf"]:
        if os.path.exists(candidate):
            return candidate
    return None

# Pre-warm font path resolution so we don't do os.path.exists per row
_font_path_cache = {}

def _get_font_path(font_name):
    if font_name not in _font_path_cache:
        _font_path_cache[font_name] = _resolve_font_path(font_name)
    return _font_path_cache[font_name]

# ── Helpers ──────────────────────────────────────────────────────────────────
def extract_data_rows(data_bytes, filename):
    """
    Extracts data from the given file bytes.
    Returns (headers: list of str, rows: list of dict)
    """
    ext = os.path.splitext(filename)[1].lower()
    headers = []
    data_rows = []

    if ext == '.txt':
        text = data_bytes.decode('utf-8')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        headers = ["Line_1"]
        data_rows = [{"Line_1": line} for line in lines]

    elif ext in ['.csv']:
        text = data_bytes.decode('utf-8')
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if rows:
            headers = [str(h).strip() for h in rows[0]]
            headers = [h if h else f"Column_{i+1}" for i, h in enumerate(headers)]
            for row in rows[1:]:
                padded_row = row + [''] * max(0, len(headers) - len(row))
                row_dict = {headers[i]: padded_row[i].strip() for i in range(len(headers))}
                if any(v for v in row_dict.values()):
                    data_rows.append(row_dict)

    elif ext in ['.xlsx', '.xls']:
        wb = load_workbook(io.BytesIO(data_bytes), data_only=True, read_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if rows:
            headers = [str(h).strip() if h is not None else f"Column_{i+1}" for i, h in enumerate(rows[0])]
            for row in rows[1:]:
                padded_row = list(row) + [None] * max(0, len(headers) - len(row))
                row_dict = {headers[i]: (str(padded_row[i]).strip() if padded_row[i] is not None else "") for i in range(len(headers))}
                if any(v for v in row_dict.values()):
                    data_rows.append(row_dict)
        wb.close()

    return headers, data_rows


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)


def _fit_font_size(draw, text, font_path, max_font_size, min_font_size, max_text_width):
    """Binary-search the largest font size where text fits within max_text_width."""
    if not font_path:
        return ImageFont.load_default()

    lo, hi = min_font_size, max_font_size
    best_size = min_font_size

    while lo <= hi:
        mid = (lo + hi) // 2
        font = _get_font(font_path, mid)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_text_width:
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return _get_font(font_path, best_size)


def draw_elements_on_image(image, elements, row_data):
    draw = ImageDraw.Draw(image)

    for el in elements:
        col_name = el.get('column', '')
        text = row_data.get(col_name, "")
        if not text:
            text = el.get('text', '')
            if not text:
                continue

        text = str(text).upper()

        text_x    = int(el.get('text_x', 100))
        text_y    = int(el.get('text_y', 390))
        text_color = hex_to_rgb(el.get('text_color', '#ffffff'))
        max_font_size  = int(el.get('max_font_size', 43))
        min_font_size  = int(el.get('min_font_size', 30))
        max_text_width = int(el.get('max_text_width', 900))
        font_name  = el.get('font', 'Roboto')

        font_path = _get_font_path(font_name)
        font = _fit_font_size(draw, text, font_path, max_font_size, min_font_size, max_text_width)

        draw.text((text_x, text_y), text, fill=text_color, font=font)


def _primary_col(elements, row):
    """Determine which column to use as the filename."""
    col = elements[0].get('column') if elements else None
    if col and col in row:
        return col
    for common in ["Name", "Participant", "Full Name", "Participant Name"]:
        if common in row:
            return common
    return list(row.keys())[0]


# ── Main generation ───────────────────────────────────────────────────────────
def generate_certificates_zip_to_file(template_bytes, data_bytes, data_filename, config):
    template_image = Image.open(io.BytesIO(template_bytes)).convert("RGB")
    headers, data_rows = extract_data_rows(data_bytes, data_filename)

    elements  = config.get('elements', [])
    seen_names = set()

    # Pre-warm font paths for all elements so _get_font_path is cached
    for el in elements:
        _get_font_path(el.get('font', 'Roboto'))

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')

    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_STORED) as zip_file:
        for i, row in enumerate(data_rows):
            image = template_image.copy()
            draw_elements_on_image(image, elements, row)

            # Build filename
            safe_name = ""
            if row:
                col = _primary_col(elements, row)
                val = row.get(col, f"cert_{i+1}")
                safe_name = "".join(c for c in str(val).upper() if c.isalnum() or c in " _-")
            if not safe_name:
                safe_name = f"cert_{i+1}"

            base = safe_name
            n = 1
            while safe_name in seen_names:
                safe_name = f"{base}_{n}"; n += 1
            seen_names.add(safe_name)

            img_buf = io.BytesIO()
            # JPEG is ~8x smaller than PNG for certificates with virtually no visual difference
            image.save(img_buf, format='JPEG', quality=85, optimize=True, subsampling=0)
            zip_file.writestr(f"{safe_name}.jpg", img_buf.getvalue())

    temp_zip.close()
    return temp_zip.name


def generate_single_preview(template_bytes, config, preview_row):
    template_image = Image.open(io.BytesIO(template_bytes)).convert("RGB")
    elements = config.get('elements', [])

    for el in elements:
        col = el.get('column', '')
        if col and not preview_row.get(col):
            preview_row[col] = "MULEARNVJC"

    image = template_image.copy()
    draw_elements_on_image(image, elements, preview_row)

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=85, optimize=True, subsampling=0)
    return img_byte_arr.getvalue()
