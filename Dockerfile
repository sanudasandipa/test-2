FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies for libtorrent and compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    libboost-all-dev \
    libssl-dev \
    libboost-python-dev \
    cmake \
    git \
    wget \
    curl \
    python3-libtorrent \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements-docker.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir -r requirements-docker.txt

# Install libtorrent from system package and create proper Python linking
RUN python3 -c "import sys; print('Python paths:', sys.path)" && \
    find /usr -name "*libtorrent*" -type f 2>/dev/null | head -10 && \
    python3 -c "
try:
    import sys
    sys.path.append('/usr/lib/python3/dist-packages')
    import libtorrent
    print('Libtorrent import successful')
except Exception as e:
    print('Libtorrent import failed:', e)
"

# Copy the rest of the application
COPY . .

# Create download directory
RUN mkdir -p /app/downloads && chmod 777 /app/downloads

# Expose the port the app will run on
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["python", "run.py"]
