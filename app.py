from flask import Flask, render_template, request, jsonify, send_file
import pytesseract
from PIL import Image
import os
import re
from docx import Document
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folders configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GENERATED_FOLDER = os.path.join(BASE_DIR, "generated_letters")
TEMPLATE_PATH = os.path.join(BASE_DIR, "scrap_template.docx")

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}

# Tesseract path (Docker has it in PATH)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_details(text):
    """Extract vehicle details from OCR text"""
    text = text.upper()
    clean_text = text.replace("\n", " ")

    logger.info("OCR TEXT: %s", text)

    # Vehicle Number (e.g., MH02AB1234)
    vehicle_match = re.search(r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b', clean_text)
    vehicle = vehicle_match.group() if vehicle_match else ""

    # Owner Name
    owner_match = re.search(r'NAME\s+([A-Z\s]+)', text)
    owner = owner_match.group(1).strip() if owner_match else ""

    # Chassis Number (17 characters)
    chassis_match = re.search(r'\b[A-Z0-9]{17}\b', clean_text)
    chassis = chassis_match.group() if chassis_match else ""

    # Engine Number (10-12 characters)
    engine_matches = re.findall(r'\b[A-Z0-9]{10,12}\b', clean_text)
    engine = ""

    for e in engine_matches:
        if e != chassis and e != vehicle:
            engine = e
            break

    # Vehicle Model
    model_match = re.search(r'MODEL\s*[:\-]?\s*([A-Z0-9 ]+)', text)
    model = model_match.group(1).strip() if model_match else ""

    return {
        "owner": owner,
        "vehicle": vehicle,
        "engine": engine,
        "chassis": chassis,
        "model": model
    }


@app.route("/")
def home():
    """Home page with upload form"""
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    """Scan vehicle document and extract details"""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: jpg, jpeg, png, pdf"}), 400

    # Generate unique filename
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(filepath)
        img = Image.open(filepath).convert("RGB")

        # Perform OCR
        text = pytesseract.image_to_string(img)
        details = extract_details(text)

        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)

        return jsonify({
            "success": True,
            "details": details
        })

    except Exception as e:
        logger.error("OCR ERROR: %s", str(e))
        return jsonify({"error": "OCR processing failed"}), 500


@app.route("/generate_letter", methods=["POST"])
def generate_letter():
    """Generate scrap letter document"""
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Check if template exists
    if not os.path.exists(TEMPLATE_PATH):
        logger.error("Template file not found: %s", TEMPLATE_PATH)
        return jsonify({"error": "Template file not found"}), 500

    try:
        document = Document(TEMPLATE_PATH)

        replacements = {
            "{{owner_name}}": data.get("owner", ""),
            "{{registration_number}}": data.get("vehicle", ""),
            "{{engine_number}}": data.get("engine", ""),
            "{{chassis_number}}": data.get("chassis", ""),
            "{{vehicle_model}}": data.get("model", ""),
            "{{date}}": data.get("date", datetime.now().strftime("%d-%m-%Y")),
            "{{city}}": data.get("city", ""),
            "{{sipl}}": data.get("sipl", ""),
            "{{handed_by}}": data.get("handed_by", ""),
            "{{pickup_address}}": data.get("pickup_address", "")
        }

        # Replace placeholders in document
        for paragraph in document.paragraphs:
            for key, value in replacements.items():
                if key in paragraph.text:
                    paragraph.text = paragraph.text.replace(key, value)

        # Generate filename
        vehicle = data.get('vehicle', 'scrap')
        filename = f"{vehicle}_Scrap_Letter.docx"
        output_path = os.path.join(GENERATED_FOLDER, filename)

        # Save document
        document.save(output_path)

        # Send file to user
        return send_file(
            output_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        logger.error("Document generation error: %s", str(e))
        return jsonify({"error": "Document generation failed"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "vehicle-ocr-app",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Render uses 8080
    logger.info(f"Starting app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)