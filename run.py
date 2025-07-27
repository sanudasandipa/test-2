import os
import uvicorn
import logging
from backend.main import app

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Entry point for the application
if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    
    # Get host from environment variable or use default
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting P2P Downloader on {host}:{port}")
    
    # Start the server
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
