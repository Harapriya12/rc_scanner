#!/usr/bin/env bash
set -o errexit

apt-get update
apt-get install -y tesseract-ocr
apt-get install -y tesseract-ocr-eng

pip install --upgrade pip
pip install -r requirements.txt