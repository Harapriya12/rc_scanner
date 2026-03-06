#!/usr/bin/env bash

# Update package lists
apt-get update

# Install Tesseract OCR and English language data
apt-get install -y tesseract-ocr
apt-get install -y tesseract-ocr-eng

# Install Python dependencies from requirements.txt
pip install -r requirements.txt