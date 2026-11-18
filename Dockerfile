FROM python:3.11-slim

# Install system dependencies (exiftool, tesseract with uzbek & english models, libheif)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libimage-exiftool-perl \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-uzb \
    libgl1 \
    libglib2.0-0 \
    libheif1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Default web port for Render/Railway/Koyeb
ENV PORT=10000

# Run bot
CMD ["python", "bot/bot.py"]
