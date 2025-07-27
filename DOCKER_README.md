# P2P Magnet Link Downloader - Docker Deployment

This document explains how to deploy the P2P Magnet Link Downloader application using Docker on Ubuntu server.

## Prerequisites

- Docker installed on your Ubuntu server
- Docker Compose installed on your system

## Ubuntu Server Installation

1. Update your system:
```bash
sudo apt update && sudo apt upgrade -y
```

2. Install Docker:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

3. Install Docker Compose:
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

4. Log out and back in for group changes to take effect.

## Deployment Instructions

1. Clone or download this repository to your Ubuntu server:
```bash
git clone <your-repo-url>
cd test-2
```

2. Make sure all required files are present:
   - `Dockerfile`
   - `docker-compose.yml`
   - `requirements-docker.txt`

### Using Docker Compose (Recommended)

1. Build and start the container:

```bash
docker-compose up -d
```

2. Check if the container is running:
```bash
docker-compose ps
```

3. View logs:
```bash
docker-compose logs -f p2p_downloader
```

4. Access the application at http://your-server-ip:8000

5. To stop the application:
```bash
docker-compose down
```

### Using Docker directly

1. Build the image:
```bash
docker build -t p2p-downloader .
```

2. Run the container:
```bash
docker run -d \
  --name p2p_downloader \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  -e ENVIRONMENT=production \
  p2p-downloader
```

## Troubleshooting

### Common Issues

1. **Permission denied errors:**
```bash
sudo chown -R $USER:$USER ./downloads
chmod 755 ./downloads
```

2. **Port already in use:**
```bash
# Change port in docker-compose.yml from 8000:8000 to another port like 8001:8000
```

3. **Container won't start:**
```bash
# Check logs
docker-compose logs p2p_downloader

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

4. **Libtorrent issues:**
   - The Docker image uses system packages for libtorrent which should work on Ubuntu
   - If issues persist, check logs for specific error messages

### Firewall Configuration

If using UFW on Ubuntu:
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

### Updating the Application

1. Pull latest changes:
```bash
git pull origin main
```

2. Rebuild and restart:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Environment Variables

You can customize the following environment variables in `docker-compose.yml`:

- `PORT`: Port to run the application (default: 8000)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `ENVIRONMENT`: Set to "production" for optimal performance

## File Structure

```
/app/
├── backend/          # Application backend
├── frontend/         # Static web files  
├── downloads/        # Downloaded files (mounted volume)
├── run.py           # Application entry point
└── requirements-docker.txt  # Python dependencies
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
