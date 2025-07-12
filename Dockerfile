# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent .pyc files and to run python in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for PDF processing by unstructured.io
# - poppler-utils: for PDF rendering
# - tesseract-ocr: for OCR in PDFs and images
# - libgl1-mesa-glx: required by OpenCV (a dependency of unstructured)
# - libmagic-dev: for accurate filetype detection
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx \
    libmagic-dev \
    && apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY ./app /app/app

# Specify the command to run on container startup
ENTRYPOINT ["python", "-m", "app"]

# Set the default command (e.g., show help)
CMD ["--help"]
