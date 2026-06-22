import os
import io
import zipfile
import csv
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
from openpyxl import load_workbook

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
            # Assume first row is header
            headers = [str(h).strip() for h in rows[0]]
            # Fallback if empty headers exist
            headers = [h if h else f"Column_{i+1}" for i, h in enumerate(headers)]
            for row in rows[1:]:
                # Zip headers with row, padding with empty strings if row is shorter
                padded_row = row + [''] * max(0, len(headers) - len(row))
                row_dict = {headers[i]: padded_row[i].strip() for i in range(len(headers))}
                # Only add if row is not entirely empty
                if any(v for v in row_dict.values()):
                    data_rows.append(row_dict)
                
    elif ext in ['.xlsx', '.xls']:
        wb = load_workbook(io.BytesIO(data_bytes), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if rows:
            headers = [str(h).strip() if h is not None else f"Column_{i+1}" for i, h in enumerate(rows[0])]
            for row in rows[1:]:
                padded_row = list(row) + [None] * max(0, len(headers) - len(row))
                row_dict = {headers[i]: (str(padded_row[i]).strip() if padded_row[i] is not None else "") for i in range(len(headers))}
                if any(v for v in row_dict.values()):
                    data_rows.append(row_dict)
                    
    return headers, data_rows

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)

def draw_elements_on_image(image, elements, row_data):
    draw = ImageDraw.Draw(image)
    
    for el in elements:
        col_name = el.get('column', '')
        text = row_data.get(col_name, "")
        if not text:
            text = el.get('text', '') # fallback to literal text
            if not text:
                continue
                
        # Capitalize the text (ALL CAPS)
        text = str(text).upper()
        
        # Configuration for this element
        text_x = int(el.get('text_x', 100))
        text_y = int(el.get('text_y', 390))
        text_color = hex_to_rgb(el.get('text_color', '#ffffff'))
        
        max_font_size = int(el.get('max_font_size', 43))
        min_font_size = int(el.get('min_font_size', 30))
        max_text_width = int(el.get('max_text_width', 900))
        
        font_name = el.get('font', 'Roboto')
        font_path = f"fonts/{font_name}.ttf"
        
        if not os.path.exists(font_path):
            font_path = "default_font.ttf"
            if not os.path.exists(font_path):
                font_path = "font.ttf"
                if not os.path.exists(font_path):
                    font_path = None
                    
        font_size = max_font_size
        
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            
        if font_path:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            
            while text_width > max_text_width and font_size > min_font_size:
                font_size -= 2
                font = ImageFont.truetype(font_path, font_size)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                
        draw.text((text_x, text_y), text, fill=text_color, font=font)

def generate_certificates_zip(template_bytes, data_bytes, data_filename, config):
    template_image = Image.open(io.BytesIO(template_bytes)).convert("RGB")
    headers, data_rows = extract_data_rows(data_bytes, data_filename)
    
    elements = config.get('elements', [])
    zip_buffer = io.BytesIO()
    seen_names = set()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, row in enumerate(data_rows):
            image = template_image.copy()
            draw_elements_on_image(image, elements, row)
            
            meta = PngInfo()
            meta.add_text("Title", "Generated Certificate")
            
            # Determine filename
            safe_name = ""
            if row:
                # 1. Try to use the column mapped to the first Text Element
                primary_col = elements[0].get('column') if elements else None
                
                # 2. Try common name columns if we still don't have one
                if not primary_col or primary_col not in row:
                    for common in ["Name", "Participant", "Full Name", "Participant Name"]:
                        if common in row:
                            primary_col = common
                            break
                            
                # 3. Fallback to the very first column in the excel
                if not primary_col or primary_col not in row:
                    primary_col = list(row.keys())[0]
                    
                val = row.get(primary_col, f"cert_{i+1}")
                safe_name = "".join(c for c in str(val).upper() if c.isalnum() or c in " _-")
                
            if not safe_name:
                safe_name = f"cert_{i+1}"
                
            # Handle duplicate names in the ZIP file
            base_name = safe_name
            counter = 1
            while safe_name in seen_names:
                safe_name = f"{base_name}_{counter}"
                counter += 1
            seen_names.add(safe_name)
            
            filename = f"{safe_name}.png"
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', pnginfo=meta)
            zip_file.writestr(filename, img_byte_arr.getvalue())
            
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def generate_single_preview(template_bytes, config, preview_row):
    template_image = Image.open(io.BytesIO(template_bytes)).convert("RGB")
    elements = config.get('elements', [])
    
    # Ensure there's always a dummy text to preview if the excel row is empty for this column
    for el in elements:
        col = el.get('column', '')
        if col and not preview_row.get(col):
            preview_row[col] = "MULEARNVJC"
            
    image = template_image.copy()
    draw_elements_on_image(image, elements, preview_row)
    
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()
