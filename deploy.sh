#!/bin/bash

# P2P Downloader Deployment Script for Ubuntu
# This script automates the deployment process on Ubuntu servers

set -e

echo "🚀 Starting P2P Downloader deployment..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root. Please run as a regular user."
   exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_status "Docker installed successfully"
    print_warning "Please log out and back in for group changes to take effect, then run this script again."
    exit 0
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_status "Docker Compose installed successfully"
fi

# Check if user is in docker group
if ! groups $USER | grep &>/dev/null '\bdocker\b'; then
    print_error "User is not in docker group. Adding user to docker group..."
    sudo usermod -aG docker $USER
    print_warning "Please log out and back in for group changes to take effect, then run this script again."
    exit 0
fi

# Check if required files exist
if [[ ! -f "docker-compose.yml" ]]; then
    print_error "docker-compose.yml not found in current directory"
    exit 1
fi

if [[ ! -f "Dockerfile" ]]; then
    print_error "Dockerfile not found in current directory"
    exit 1
fi

if [[ ! -f "requirements-docker.txt" ]]; then
    print_error "requirements-docker.txt not found in current directory"
    exit 1
fi

# Create downloads directory if it doesn't exist
if [[ ! -d "downloads" ]]; then
    mkdir -p downloads
    print_status "Created downloads directory"
fi

# Set proper permissions
chmod 755 downloads
print_status "Set proper permissions for downloads directory"

# Stop existing container if running
if docker-compose ps | grep -q "p2p_downloader"; then
    print_warning "Stopping existing container..."
    docker-compose down
fi

# Build and start the application
print_status "Building and starting P2P Downloader..."
docker-compose up -d --build

# Wait for container to be healthy
print_status "Waiting for container to be healthy..."
sleep 10

# Check if container is running
if docker-compose ps | grep -q "Up"; then
    print_status "P2P Downloader is running successfully!"
    
    # Get the host IP
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "🌐 Access your P2P Downloader at:"
    echo "   Local: http://localhost:8000"
    echo "   Network: http://${HOST_IP}:8000"
    echo ""
    
    # Check if UFW is active and port needs to be opened
    if command -v ufw &> /dev/null && sudo ufw status | grep -q "Status: active"; then
        if ! sudo ufw status | grep -q "8000"; then
            print_warning "UFW firewall is active. Opening port 8000..."
            sudo ufw allow 8000/tcp
            sudo ufw reload
            print_status "Port 8000 opened in firewall"
        fi
    fi
    
    echo "📊 To view logs: docker-compose logs -f p2p_downloader"
    echo "🛑 To stop: docker-compose down"
    echo "🔄 To restart: docker-compose restart"
    echo ""
    print_status "Deployment completed successfully!"
    
else
    print_error "Container failed to start. Check logs with: docker-compose logs p2p_downloader"
    exit 1
fi
