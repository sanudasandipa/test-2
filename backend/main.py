import os
import uuid
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Set up logging first
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try different import methods for libtorrent
try:
    import libtorrent as lt
    logger.info("Successfully imported libtorrent")
except ImportError:
    try:
        from libtorrent import libtorrent as lt
        logger.info("Successfully imported libtorrent (alternative method)")
    except ImportError:
        try:
            # Try system package import
            import sys
            sys.path.append('/usr/lib/python3/dist-packages')
            import libtorrent as lt
            logger.info("Successfully imported libtorrent (system package)")
        except ImportError:
            logger.error("Failed to import libtorrent. Make sure it's properly installed.")
            # Fallback to qbittorrent API mode
            lt = None

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

# Initialize libtorrent session
session = None
if lt:
    try:
        session = lt.session()
        session.listen_on(6881, 6891)  # Set ports for incoming connections
        logger.info("Libtorrent session initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize libtorrent session: {e}")
        session = None
else:
    logger.warning("Libtorrent not available, some features may be limited")

# Store active downloads
active_downloads = {}  # handle_id -> {"handle": lt.torrent_handle, "info": {...}}

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

def get_download_info(handle_id: str, handle) -> DownloadInfo:
    """Get download information from a torrent handle"""
    if not handle or not handle.is_valid():
        return None
    
    status = handle.status()
    
    if not status.has_metadata:
        info = {"id": handle_id,
                "name": "Fetching Metadata...",
                "status": "metadata",
                "progress": 0,
                "download_speed": 0,
                "upload_speed": 0,
                "num_peers": 0,
                "total_size": 0,
                "downloaded": 0,
                "remaining_time": None,
                "save_path": DOWNLOAD_DIR}
    else:
        if lt:
            state_str = {
                lt.torrent_status.seeding: "seeding",
                lt.torrent_status.downloading: "downloading",
                lt.torrent_status.finished: "finished",
                lt.torrent_status.checking_files: "checking",
                lt.torrent_status.checking_resume_data: "checking resume",
            }.get(status.state, "unknown")
        else:
            # Fallback status mapping without libtorrent constants
            state_str = "unknown"
        
        # Calculate remaining time
        remaining = None
        if status.download_rate > 0:
            remaining = int((status.total_wanted - status.total_wanted_done) / status.download_rate)
        
        info = {
            "id": handle_id,
            "name": handle.name() if handle.has_metadata() else "Unknown",
            "status": state_str,
            "progress": status.progress * 100,
            "download_speed": status.download_rate,
            "upload_speed": status.upload_rate,
            "num_peers": status.num_peers,
            "total_size": status.total_wanted,
            "downloaded": status.total_wanted_done,
            "remaining_time": remaining,
            "save_path": status.save_path
        }
    
    return info

# Background task for updating torrent status
async def update_torrent_status():
    while True:
        updates = []
        for handle_id, data in list(active_downloads.items()):
            handle = data["handle"]
            if not handle.is_valid():
                continue
                
            info = get_download_info(handle_id, handle)
            if info:
                data["info"] = info
                updates.append(info)
                
                # Remove completed torrents after seeding
                if session:
                    status = handle.status()
                    if status.is_seeding and status.all_time_upload > 2 * status.total_wanted:
                        logger.info(f"Torrent {handle.name()} has seeded enough, removing from session")
                        session.remove_torrent(handle)
                        del active_downloads[handle_id]
        
        if updates:
            await manager.broadcast({"type": "updates", "data": updates})
        
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_torrent_status())

@app.post("/api/download", response_model=Dict)
async def start_download(request: MagnetLinkRequest):
    try:
        if not lt or not session:
            raise HTTPException(status_code=503, detail="Libtorrent service not available")
            
        save_path = request.save_path if request.save_path else DOWNLOAD_DIR
        
        # Create handle from magnet link
        params = lt.parse_magnet_uri(request.magnet_link)
        params.save_path = save_path
        
        handle = session.add_torrent(params)
        
        # Generate unique ID for this download
        handle_id = str(uuid.uuid4())
        
        # Add to active downloads
        active_downloads[handle_id] = {
            "handle": handle,
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
    
    if not session or not lt:
        raise HTTPException(status_code=503, detail="Libtorrent service not available")
    
    handle = active_downloads[download_id]["handle"]
    session.remove_torrent(handle, lt.session.delete_files)
    del active_downloads[download_id]
    
    return {"success": True, "message": "Download canceled"}

@app.get("/api/download/{download_id}/pause")
async def pause_download(download_id: str):
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    handle = active_downloads[download_id]["handle"]
    handle.pause()
    
    return {"success": True, "message": "Download paused"}

@app.get("/api/download/{download_id}/resume")
async def resume_download(download_id: str):
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    handle = active_downloads[download_id]["handle"]
    handle.resume()
    
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

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy", 
        "libtorrent_available": lt is not None and session is not None,
        "downloads_active": len(active_downloads)
    }

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
