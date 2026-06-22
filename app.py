from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
from certificate_service import generate_certificates_zip, extract_data_rows, generate_single_preview
import io
import json

app = Flask(__name__)
CORS(app) # Enable CORS for all domains so Vercel frontend can communicate with Render backend

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse-headers', methods=['POST'])
def parse_headers():
    if 'excel' not in request.files:
        return jsonify({"error": "Missing data file"}), 400
    try:
        data_file = request.files['excel']
        data_bytes = data_file.read()
        headers, rows = extract_data_rows(data_bytes, data_file.filename)
        return jsonify({"headers": headers, "preview_row": rows[0] if rows else {}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    if 'template' not in request.files or 'excel' not in request.files:
        return jsonify({"error": "Missing template or data file"}), 400
        
    template_file = request.files['template']
    data_file = request.files['excel']
    
    if template_file.filename == '' or data_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        template_bytes = template_file.read()
        data_bytes = data_file.read()
        
        config_str = request.form.get('config', '{}')
        config = json.loads(config_str)
        
        zip_bytes = generate_certificates_zip(template_bytes, data_bytes, data_file.filename, config)
        
        return send_file(
            io.BytesIO(zip_bytes),
            mimetype='application/zip',
            as_attachment=True,
            download_name='certificates.zip'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    if 'template' not in request.files:
        return jsonify({"error": "Missing template file"}), 400
        
    template_file = request.files['template']
    if template_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        template_bytes = template_file.read()
        
        config_str = request.form.get('config', '{}')
        config = json.loads(config_str)
        
        preview_row_str = request.form.get('preview_row', '{}')
        preview_row = json.loads(preview_row_str)
        
        img_bytes = generate_single_preview(template_bytes, config, preview_row)
        
        return send_file(
            io.BytesIO(img_bytes),
            mimetype='image/png'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
