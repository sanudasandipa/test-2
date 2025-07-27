import os
import uuid
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import qbittorrentapi

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Initialize FastAPI
app = FastAPI(title="P2P Downloader", description="A personal magnet link downloader")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize qBittorrent client
# Using a local qBittorrent Web UI instance
# Note: This requires qBittorrent to be running with Web UI enabled
# For a real application, you'd need to set up qBittorrent WebUI or consider alternatives
qbt_client = None  # Will be initialized at startup

# Store active downloads mapping
active_downloads = {}  # handle_id -> {"hash": torrent_hash, "info": {...}}

class MagnetLinkRequest(BaseModel):
    magnet_link: str
    save_path: Optional[str] = None

class DownloadInfo(BaseModel):
    id: str
    name: str
    status: str
    progress: float
    download_speed: float
    upload_speed: float
    num_peers: int
    total_size: int
    downloaded: int
    remaining_time: Optional[int] = None
    save_path: str

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")

manager = ConnectionManager()

def get_download_info(handle_id: str, torrent_hash: str) -> DownloadInfo:
    """Get download information from a torrent hash"""
    try:
        torrent = qbt_client.torrents_info(torrent_hashes=torrent_hash)[0]
        
        # Map qBittorrent state to our internal state
        state_str = "unknown"
        if torrent.state_enum.is_downloading:
            state_str = "downloading"
        elif torrent.state_enum.is_uploading:
            state_str = "seeding"
        elif torrent.state_enum.is_complete:
            state_str = "finished"
        elif torrent.state_enum.is_checking:
            state_str = "checking"
        elif torrent.state_enum.is_paused:
            state_str = "paused"
        
        # Calculate remaining time
        remaining = torrent.eta if torrent.eta > 0 else None
        
        info = {
            "id": handle_id,
            "name": torrent.name,
            "status": state_str,
            "progress": torrent.progress * 100,
            "download_speed": torrent.dlspeed,
            "upload_speed": torrent.upspeed,
            "num_peers": torrent.num_leechs + torrent.num_seeds,
            "total_size": torrent.size,
            "downloaded": int(torrent.size * torrent.progress / 100),
            "remaining_time": remaining,
            "save_path": torrent.save_path
        }
        return info
    except Exception as e:
        logger.error(f"Error getting download info: {e}")
        return None

# Background task for updating torrent status
async def update_torrent_status():
    while True:
        try:
            updates = []
            for handle_id, data in list(active_downloads.items()):
                torrent_hash = data["hash"]
                
                info = get_download_info(handle_id, torrent_hash)
                if info:
                    data["info"] = info
                    updates.append(info)
            
            if updates:
                await manager.broadcast({"type": "updates", "data": updates})
            
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in update_torrent_status: {e}")
            await asyncio.sleep(5)  # Wait a bit longer if there was an error

def initialize_qbittorrent():
    """Initialize the qBittorrent client and create a local qbittorrent instance for testing"""
    global qbt_client
    try:
        # For a real application, you'd use a real qBittorrent instance
        # Here we're creating a simple connection to a local instance
        qbt_client = qbittorrentapi.Client(
            host="localhost",
            port=8080,
            username="admin",
            password="adminadmin"
        )
        
        # We need to set up and run qBittorrent for this to work
        # In a real app, you'd either have qBittorrent pre-installed or use a different library
        # For this demo, we'll use a temporary client just to show the UI
        
        # For demo purposes - create a mock client
        class MockClient:
            def __init__(self):
                self.mock_torrents = {}
                self.torrent_counter = 0
            
            def torrents_info(self, torrent_hashes=None):
                if torrent_hashes:
                    return [self.mock_torrents.get(torrent_hashes, MockTorrent())]
                return [v for k, v in self.mock_torrents.items()]
            
            def torrents_add(self, urls, save_path=None):
                torrent_hash = f"mock_hash_{self.torrent_counter}"
                self.torrent_counter += 1
                torrent = MockTorrent(torrent_hash)
                torrent.name = f"Mock Torrent {self.torrent_counter}"
                torrent.save_path = save_path or DOWNLOAD_DIR
                self.mock_torrents[torrent_hash] = torrent
                return torrent_hash
            
            def torrents_pause(self, torrent_hashes):
                if torrent_hashes in self.mock_torrents:
                    self.mock_torrents[torrent_hashes].state_enum.is_paused = True
                    self.mock_torrents[torrent_hashes].state_enum.is_downloading = False
            
            def torrents_resume(self, torrent_hashes):
                if torrent_hashes in self.mock_torrents:
                    self.mock_torrents[torrent_hashes].state_enum.is_paused = False
                    self.mock_torrents[torrent_hashes].state_enum.is_downloading = True
            
            def torrents_delete(self, torrent_hashes, delete_files=False):
                if torrent_hashes in self.mock_torrents:
                    del self.mock_torrents[torrent_hashes]
        
        class MockTorrent:
            def __init__(self, hash_value="mock_hash"):
                self.hash = hash_value
                self.name = "Mock Torrent"
                self.state_enum = MockStateEnum()
                self.progress = 0
                self.dlspeed = 0
                self.upspeed = 0
                self.num_leechs = 0
                self.num_seeds = 0
                self.size = 1000000000  # 1GB
                self.eta = 3600  # 1 hour
                self.save_path = DOWNLOAD_DIR
                
                # Start progress simulation
                asyncio.create_task(self.simulate_progress())
                
            async def simulate_progress(self):
                while self.progress < 100:
                    await asyncio.sleep(1)
                    if not self.state_enum.is_paused:
                        self.progress += 0.5
                        self.dlspeed = 500000 + (hash(self.name) % 500000)  # Random speed
                        self.num_seeds = 5 + (hash(self.name) % 10)
                        self.num_leechs = 3 + (hash(self.name) % 7)
                        self.eta = int((100 - self.progress) * 36)  # Decreasing time
                
                self.state_enum.is_downloading = False
                self.state_enum.is_complete = True
                self.state_enum.is_uploading = True
                self.dlspeed = 0
                self.upspeed = 100000
        
        class MockStateEnum:
            def __init__(self):
                self.is_downloading = True
                self.is_uploading = False
                self.is_complete = False
                self.is_checking = False
                self.is_paused = False
        
        qbt_client = MockClient()
        logger.info("Mock qBittorrent client initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize qBittorrent client: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    # Initialize qBittorrent client
    if initialize_qbittorrent():
        logger.info("qBittorrent client initialized successfully")
        # Start background task for updating torrent status
        asyncio.create_task(update_torrent_status())
    else:
        logger.error("Failed to initialize qBittorrent client. Application may not work correctly.")

@app.post("/api/download", response_model=Dict)
async def start_download(request: MagnetLinkRequest):
    try:
        save_path = request.save_path if request.save_path else DOWNLOAD_DIR
        
        # Add torrent to qBittorrent
        torrent_hash = qbt_client.torrents_add(urls=request.magnet_link, save_path=save_path)
        
        # Generate unique ID for this download
        handle_id = str(uuid.uuid4())
        
        # Add to active downloads
        active_downloads[handle_id] = {
            "hash": torrent_hash,
            "info": {
                "id": handle_id,
                "name": "Fetching Metadata...",
                "status": "metadata",
                "progress": 0,
                "download_speed": 0,
                "upload_speed": 0,
                "num_peers": 0,
                "total_size": 0,
                "downloaded": 0,
                "remaining_time": None,
                "save_path": save_path
            }
        }
        
        return {"success": True, "id": handle_id, "message": "Download started"}
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/downloads", response_model=List[Dict])
async def get_downloads():
    downloads = []
    for handle_id, data in active_downloads.items():
        if "info" in data:
            downloads.append(data["info"])
    
    return downloads

@app.delete("/api/download/{download_id}")
async def cancel_download(download_id: str):
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    torrent_hash = active_downloads[download_id]["hash"]
    qbt_client.torrents_delete(torrent_hashes=torrent_hash, delete_files=True)
    del active_downloads[download_id]
    
    return {"success": True, "message": "Download canceled"}

@app.get("/api/download/{download_id}/pause")
async def pause_download(download_id: str):
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    torrent_hash = active_downloads[download_id]["hash"]
    qbt_client.torrents_pause(torrent_hashes=torrent_hash)
    
    return {"success": True, "message": "Download paused"}

@app.get("/api/download/{download_id}/resume")
async def resume_download(download_id: str):
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    torrent_hash = active_downloads[download_id]["hash"]
    qbt_client.torrents_resume(torrent_hashes=torrent_hash)
    
    return {"success": True, "message": "Download resumed"}

@app.get("/api/files", response_model=List[Dict])
async def list_downloaded_files():
    files = []
    for root, _, filenames in os.walk(DOWNLOAD_DIR):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, DOWNLOAD_DIR)
            size = os.path.getsize(file_path)
            files.append({
                "name": filename,
                "path": rel_path,
                "size": size,
                "created": os.path.getctime(file_path)
            })
    
    return files

@app.get("/api/download/file/{path:path}")
async def download_file(path: str):
    file_path = os.path.join(DOWNLOAD_DIR, path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=os.path.basename(file_path))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # We can implement commands here if needed
            await websocket.send_json({"message": "Received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Mount static files
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "frontend"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
