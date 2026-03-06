from flask import Flask, render_template, request, jsonify, send_file
import pytesseract
from PIL import Image
import os
import re
from docx import Document

app = Flask(__name__)

# Base directory (important for Render deployment)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GENERATED_FOLDER = os.path.join(BASE_DIR, "generated_letters")
TEMPLATE_PATH = os.path.join(BASE_DIR, "scrap_template.docx")

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Tesseract configuration
if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


def extract_details(text):

    text = text.upper()
    clean_text = text.replace("\n", " ")

    print("OCR TEXT:", text)

    # Vehicle Number
    vehicle_match = re.search(r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b', clean_text)
    vehicle = vehicle_match.group() if vehicle_match else ""

    # Owner Name
    owner_match = re.search(r'NAME\s+([A-Z\s]+)', text)
    owner = owner_match.group(1).strip() if owner_match else ""

    # Chassis Number
    chassis_match = re.search(r'\b[A-Z0-9]{17}\b', clean_text)
    chassis = chassis_match.group() if chassis_match else ""

    # Engine Number
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
    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"})

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        img = Image.open(filepath)

        # OCR
        text = pytesseract.image_to_string(img)
        details = extract_details(text)

        return jsonify(details)

    except Exception as e:
        print("OCR ERROR:", str(e))
        return jsonify({"error": "OCR processing failed"})


@app.route("/generate_letter", methods=["POST"])
def generate_letter():

    data = request.json

    document = Document(TEMPLATE_PATH)

    replacements = {
        "{{owner_name}}": data.get("owner", ""),
        "{{registration_number}}": data.get("vehicle", ""),
        "{{engine_number}}": data.get("engine", ""),
        "{{chassis_number}}": data.get("chassis", ""),
        "{{vehicle_model}}": data.get("model", ""),
        "{{date}}": data.get("date", ""),
        "{{city}}": data.get("city", ""),
        "{{sipl}}": data.get("sipl", ""),
        "{{handed_by}}": data.get("handed_by", ""),
        "{{pickup_address}}": data.get("pickup_address", "")
    }

    for paragraph in document.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value)

    filename = f"{data.get('vehicle','scrap')}_Scrap_Letter.docx"
    output_path = os.path.join(GENERATED_FOLDER, filename)

    document.save(output_path)

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)