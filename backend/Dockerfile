# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy app directory maintaining structure
COPY app/ ./app/

# Copy additional required directories
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY tools/ ./tools/
COPY development/ ./development/

# Copy the startup scripts to the root
COPY start.py ./
COPY start_frontend.sh ./

# Set Python path to ensure modules can be found
ENV PYTHONPATH=/app:$PYTHONPATH

# Make the startup scripts executable
RUN chmod +x start.py
RUN chmod +x start_frontend.sh

# Expose port (Railway will set the PORT environment variable)
EXPOSE $PORT

# Use the smart startup script that checks SERVICE_TYPE
CMD ["python", "start.py"] 