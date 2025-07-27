# P2P Magnet Link Downloader - Docker Deployment

This document explains how to deploy the P2P Magnet Link Downloader application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system

## Deployment Instructions

1. Clone or download this repository to your local machine
2. Navigate to the project directory

### Using Docker Compose (Recommended)

1. Build and start the container:

```bash
docker-compose up -d
```

2. Access the application at http://localhost:8000

3. To stop the application:

```bash
docker-compose down
```

### Using Docker Directly

1. Build the Docker image:

```bash
docker build -t p2p-downloader .
```

2. Run the container:

```bash
docker run -d -p 8000:8000 -v ./downloads:/app/downloads --name p2p_downloader p2p-downloader
```

3. To stop the container:

```bash
docker stop p2p_downloader
```

## Configuration

- You can modify the port and other settings in the docker-compose.yml file
- Downloaded files will be stored in the ./downloads directory on your host machine

## Notes

- Make sure ports 6881-6891 are available for P2P connections
- For production deployment, consider setting up proper authentication and security measures
