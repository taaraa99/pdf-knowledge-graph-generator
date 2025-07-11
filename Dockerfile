# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent .pyc files and to run python in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for PDF processing by unstructured.io
# poppler-utils is for PDF rendering, and tesseract-ocr is for OCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && apt-get clean

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code, data, and configuration files
# These paths match your folder structure
COPY ./app /app/app
COPY ./data /app/data
COPY ontology.json .
COPY .env .

# Specify the command to run on container startup
ENTRYPOINT ["python", "-m", "app"]

# Set the default command (e.g., show help)
CMD ["--help"]
