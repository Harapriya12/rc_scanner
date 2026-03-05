import pytesseract
from PIL import Image
import os
import re

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Get current folder path
current_folder = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(current_folder, "test_image.jpeg")

print("Looking for image at:", image_path)

# Extract text
img = Image.open(image_path)
text = pytesseract.image_to_string(img)

print("\nFull Extracted Text:\n")
print(text)

# ----------- Clean & Extract Required Details -----------

# Clean text (remove extra spaces)
clean_text = text.replace("\n", " ")

# Vehicle Number (Indian RC format)
vehicle_match = re.search(r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b', clean_text)
vehicle_number = vehicle_match.group() if vehicle_match else "Not Found"

# Owner Name (Next line after NAME)
owner_match = re.search(r'NAME\s+([A-Z\s]+?)\s{2,}', text)
owner_name = owner_match.group(1).strip() if owner_match else "Not Found"

# Chassis Number (VIN starting with MD, 17 characters)
chassis_match = re.search(r'\bMD[A-Z0-9]{15}\b', clean_text)
chassis_number = chassis_match.group() if chassis_match else "Not Found"

# Engine Number (10-15 alphanumeric characters, not vehicle number)
engine_match = re.search(r'\b(?!' + vehicle_number + r'\b)[A-Z0-9]{10,15}\b', clean_text)
engine_number = engine_match.group() if engine_match else "Not Found"

print("\n--------- Extracted Details ---------")
print("Vehicle Number:", vehicle_number)
print("Owner Name:", owner_name)
print("Engine Number:", engine_number)
print("Chassis Number:", chassis_number)