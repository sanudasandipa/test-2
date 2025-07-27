FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies for libtorrent
RUN apt-get update && apt-get install -y \
    build-essential \
    libboost-all-dev \
    libssl-dev \
    libboost-python-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
# Install dependencies with retry mechanism
RUN pip install --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt || \
    (pip install --no-cache-dir python-libtorrent && \
     pip install --no-cache-dir -r requirements.txt)

# Copy the rest of the application
COPY . .

# Create download directory
RUN mkdir -p /app/downloads && chmod 777 /app/downloads

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application
CMD ["python", "run.py"]
