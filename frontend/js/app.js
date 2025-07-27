document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const magnetInput = document.getElementById('magnet-link');
    const downloadBtn = document.getElementById('download-btn');
    const downloadsList = document.getElementById('downloads-list');
    const filesList = document.getElementById('files-list');
    const emptyDownloads = document.getElementById('empty-downloads');
    const emptyFiles = document.getElementById('empty-files');
    const downloadError = document.getElementById('download-error');
    
    // Templates
    const downloadTemplate = document.getElementById('download-template');
    const fileTemplate = document.getElementById('file-template');
    
    // WebSocket
    let ws = null;
    
    // Active downloads tracking
    const activeDownloads = new Map();
    
    // Initialize
    initApp();
    
    // Functions
    function initApp() {
        // Set up WebSocket connection
        setupWebSocket();
        
        // Fetch initial data
        fetchDownloads();
        fetchFiles();
        
        // Add event listeners
        downloadBtn.addEventListener('click', startDownload);
        
        // Add debounced input listener for validation
        magnetInput.addEventListener('input', debounce(() => {
            if (magnetInput.value.trim() && !isValidMagnet(magnetInput.value.trim())) {
                showError('Invalid magnet link format');
            } else {
                hideError();
            }
        }, 300));
    }
    
    function setupWebSocket() {
        // Close existing connection if any
        if (ws) {
            ws.close();
        }
        
        // Create new WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('WebSocket connection established');
        };
        
        ws.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code, event.reason);
            // Try to reconnect after delay
            setTimeout(() => {
                console.log('Attempting to reconnect WebSocket...');
                setupWebSocket();
            }, 5000);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'updates' && Array.isArray(data.data)) {
                data.data.forEach(updateDownload);
            }
        };
    }
    
    async function fetchDownloads() {
        try {
            const response = await fetch('/api/downloads');
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const downloads = await response.json();
            
            // Clear existing downloads view
            const downloadElements = downloadsList.querySelectorAll('.download-item');
            downloadElements.forEach(el => {
                if (!el.classList.contains('template')) {
                    el.remove();
                }
            });
            
            // Add downloads to the list
            downloads.forEach(download => {
                updateDownload(download);
            });
            
            // Show/hide empty state
            toggleEmptyState(emptyDownloads, downloads.length === 0);
            
        } catch (error) {
            console.error('Failed to fetch downloads:', error);
        }
    }
    
    async function fetchFiles() {
        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const files = await response.json();
            
            // Clear existing files view
            while (filesList.firstChild && !filesList.firstChild.id) {
                filesList.removeChild(filesList.firstChild);
            }
            
            // Add files to the list
            files.forEach(file => {
                const fileEl = createFileElement(file);
                if (emptyFiles.nextSibling) {
                    filesList.insertBefore(fileEl, emptyFiles.nextSibling);
                } else {
                    filesList.appendChild(fileEl);
                }
            });
            
            // Show/hide empty state
            toggleEmptyState(emptyFiles, files.length === 0);
            
        } catch (error) {
            console.error('Failed to fetch files:', error);
        }
    }
    
    async function startDownload() {
        const magnetLink = magnetInput.value.trim();
        
        if (!magnetLink) {
            showError('Please enter a magnet link');
            return;
        }
        
        if (!isValidMagnet(magnetLink)) {
            showError('Invalid magnet link format');
            return;
        }
        
        hideError();
        
        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    magnet_link: magnetLink
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Clear input
                magnetInput.value = '';
                
                // Success message could be shown here
                console.log('Download started successfully:', data.id);
                
                // Fetch latest downloads
                fetchDownloads();
            }
            
        } catch (error) {
            showError(error.message);
        }
    }
    
    async function cancelDownload(downloadId) {
        try {
            const response = await fetch(`/api/download/${downloadId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            // Remove element from DOM
            const element = document.querySelector(`.download-item[data-id="${downloadId}"]`);
            if (element) {
                element.remove();
            }
            
            // Remove from tracking map
            activeDownloads.delete(downloadId);
            
            // Update empty state
            toggleEmptyState(emptyDownloads, downloadsList.querySelectorAll('.download-item').length === 0);
            
        } catch (error) {
            console.error('Failed to cancel download:', error);
        }
    }
    
    async function pauseDownload(downloadId, button) {
        try {
            const response = await fetch(`/api/download/${downloadId}/pause`);
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            // Toggle buttons
            const pauseBtn = button;
            const resumeBtn = button.parentNode.querySelector('.resume-btn');
            
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'inline-block';
            
        } catch (error) {
            console.error('Failed to pause download:', error);
        }
    }
    
    async function resumeDownload(downloadId, button) {
        try {
            const response = await fetch(`/api/download/${downloadId}/resume`);
            
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            // Toggle buttons
            const resumeBtn = button;
            const pauseBtn = button.parentNode.querySelector('.pause-btn');
            
            resumeBtn.style.display = 'none';
            pauseBtn.style.display = 'inline-block';
            
        } catch (error) {
            console.error('Failed to resume download:', error);
        }
    }
    
    function updateDownload(data) {
        // Check if we already have this download in DOM
        let element = document.querySelector(`.download-item[data-id="${data.id}"]`);
        
        if (!element) {
            // Create a new element from template
            element = createDownloadElement(data);
            
            // Add to DOM
            if (emptyDownloads) {
                emptyDownloads.style.display = 'none';
            }
            
            if (emptyDownloads.nextSibling) {
                downloadsList.insertBefore(element, emptyDownloads.nextSibling);
            } else {
                downloadsList.appendChild(element);
            }
        }
        
        // Update the element with current data
        updateDownloadElement(element, data);
        
        // Track download
        activeDownloads.set(data.id, data);
        
        // Hide empty state if needed
        toggleEmptyState(emptyDownloads, false);
    }
    
    function createDownloadElement(data) {
        const template = downloadTemplate.content.cloneNode(true);
        const element = template.querySelector('.download-item');
        
        // Set download ID
        element.setAttribute('data-id', data.id);
        
        // Add event listeners
        const cancelBtn = element.querySelector('.cancel-btn');
        const pauseBtn = element.querySelector('.pause-btn');
        const resumeBtn = element.querySelector('.resume-btn');
        
        cancelBtn.addEventListener('click', () => cancelDownload(data.id));
        pauseBtn.addEventListener('click', (e) => pauseDownload(data.id, e.target.closest('.pause-btn')));
        resumeBtn.addEventListener('click', (e) => resumeDownload(data.id, e.target.closest('.resume-btn')));
        
        return element;
    }
    
    function updateDownloadElement(element, data) {
        // Update download name
        element.querySelector('.download-name').textContent = data.name;
        
        // Update progress bar
        const progressBar = element.querySelector('.download-progress-bar');
        const progressText = element.querySelector('.download-progress-text');
        const progress = Math.round(data.progress);
        
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        
        // Update details
        element.querySelector('.status').textContent = capitalizeFirstLetter(data.status);
        element.querySelector('.size').textContent = formatBytes(data.total_size);
        element.querySelector('.download-speed').textContent = `${formatBytes(data.download_speed)}/s`;
        element.querySelector('.time-remaining').textContent = formatTimeRemaining(data.remaining_time);
        element.querySelector('.peers').textContent = data.num_peers;
        
        // Update download button visibility based on status
        const pauseBtn = element.querySelector('.pause-btn');
        const resumeBtn = element.querySelector('.resume-btn');
        
        if (data.status === 'downloading') {
            pauseBtn.style.display = 'inline-block';
            resumeBtn.style.display = 'none';
        } else if (data.status === 'paused') {
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'inline-block';
        } else if (data.status === 'finished' || data.status === 'seeding') {
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = 'none';
        }
    }
    
    function createFileElement(file) {
        const template = fileTemplate.content.cloneNode(true);
        const element = template.querySelector('.file-item');
        
        // Set file details
        element.querySelector('.file-name').textContent = file.name;
        element.querySelector('.file-size').textContent = formatBytes(file.size);
        element.querySelector('.file-date').textContent = formatDate(file.created);
        
        // Set download link
        const downloadLink = element.querySelector('.download-file-btn');
        downloadLink.href = `/api/download/file/${encodeURIComponent(file.path)}`;
        downloadLink.download = file.name;
        
        return element;
    }
    
    function toggleEmptyState(element, show) {
        if (element) {
            element.style.display = show ? 'flex' : 'none';
        }
    }
    
    function showError(message) {
        downloadError.textContent = message;
        downloadError.style.display = 'block';
    }
    
    function hideError() {
        downloadError.textContent = '';
        downloadError.style.display = 'none';
    }
    
    // Utility functions
    function isValidMagnet(magnet) {
        return magnet.startsWith('magnet:?');
    }
    
    function formatBytes(bytes, decimals = 2) {
        if (!bytes || bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }
    
    function formatTimeRemaining(seconds) {
        if (!seconds || seconds < 0) return 'Unknown';
        
        if (seconds < 60) {
            return `${seconds} sec`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)} min ${seconds % 60} sec`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours} hr ${minutes} min`;
        }
    }
    
    function formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleDateString();
    }
    
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
    
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
});
