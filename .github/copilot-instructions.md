<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# P2P Magnet Link Downloader Project

This is a P2P magnet link downloader application with a Python FastAPI backend and HTML/CSS/JS frontend.

## Project Structure

- `backend/`: Contains the FastAPI backend code
  - `main.py`: Main FastAPI application with torrent handling logic
- `frontend/`: Contains the HTML, CSS, and JS files for the UI
  - `index.html`: Main HTML file
  - `css/styles.css`: CSS styles
  - `js/app.js`: Frontend JavaScript code
- `downloads/`: Directory where downloaded files are stored
- `run.py`: Entry point to run the application
- `requirements.txt`: Python dependencies

## Technologies

- Backend: Python, FastAPI, libtorrent
- Frontend: HTML5, CSS3, JavaScript
- Communication: REST API and WebSockets

## Dependencies

- FastAPI - Web framework
- libtorrent - Torrent handling
- uvicorn - ASGI server
- websockets - For real-time updates
- python-dotenv - For environment variables

When suggesting code changes:
1. Maintain the separation between backend and frontend components
2. Consider websocket implementation for real-time updates
3. Be aware of proper error handling for network operations
4. Consider the asynchronous nature of torrent downloads
