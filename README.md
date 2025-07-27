# P2P Magnet Link Downloader

A personal P2P downloader application with a Python backend and HTML/CSS frontend for downloading and managing torrent files from magnet links.

## Features

- Download torrents using magnet links
- Monitor download progress in real-time via WebSockets
- View and download completed files
- Responsive web interface
- Support for both libtorrent and qBittorrent backends

## Requirements

- Python 3.8 or higher
- FastAPI and Uvicorn
- Either:
  - libtorrent library for direct torrent handling
  - qBittorrent (with Web UI enabled) for the alternative backend

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/P2P_Downloader.git
cd P2P_Downloader
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Note: Installing `libtorrent` can be challenging on some platforms. If you encounter issues:

#### Option 1: Use the qBittorrent backend instead
Install qBittorrent on your system and enable the Web UI. Then use `run_qbit.py` instead of `run.py`.

#### Option 2: Install libtorrent through your system's package manager

```bash
# Ubuntu/Debian
sudo apt-get install python3-libtorrent

# Arch Linux
sudo pacman -S python-libtorrent

# macOS (Homebrew)
brew install libtorrent-rasterbar

# Windows (using Anaconda)
conda install -c conda-forge libtorrent
```

### 3. Create a downloads folder

```bash
mkdir downloads
```

## Usage

### Start the application

```bash
python run.py
```

By default, the server will start on `http://localhost:8000`.

### Using the application

1. Open your web browser and navigate to `http://localhost:8000`
2. Paste a magnet link into the input field
3. Click the "Download" button
4. Monitor your downloads in the "Active Downloads" section
5. Access completed downloads in the "Downloaded Files" section

## Configuration

You can configure the following environment variables:

- `PORT`: The port on which the server runs (default: 8000)
- `HOST`: The host interface to bind to (default: 0.0.0.0)

## Notes

- This application is for personal use only
- Be aware of the legal implications of downloading copyrighted content in your region
- Download speeds may vary based on the availability of seeders and your network connection

## License

MIT License
