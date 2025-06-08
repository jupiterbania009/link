import config from './config.js';

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const videoUrl = document.getElementById('videoUrl');
    const playBtn = document.getElementById('playBtn');
    const videoPlayer = document.getElementById('videoPlayer');
    const placeholder = document.getElementById('placeholder');
    const downloadSection = document.getElementById('downloadSection');
    const downloadOptions = document.querySelectorAll('.download-option');
    const downloadBtn = document.getElementById('downloadBtn');
    
    // State variables
    let currentVideoUrl = '';
    let selectedQuality = '';
    let videoInfo = null;
    
    // API endpoints
    const API_ENDPOINTS = {
        VIDEO_INFO: `${config.API_BASE_URL}/api/video-info`,
        DOWNLOAD: `${config.API_BASE_URL}/api/download`
    };
    
    // Play button click event
    playBtn.addEventListener('click', handlePlayClick);
    
    // Download option selection
    downloadOptions.forEach(option => {
        option.addEventListener('click', function() {
            const quality = this.getAttribute('data-quality');
            if (this.classList.contains('unavailable')) {
                showNotification(`Quality ${quality} is not available for this video`, 'error');
                return;
            }
            
            // Remove active class from all options
            downloadOptions.forEach(opt => opt.classList.remove('active'));
            // Add active class to selected option
            this.classList.add('active');
            selectedQuality = quality;
            
            showNotification(`Selected quality: ${quality}`, 'success');
        });
    });
    
    // Download button click event
    downloadBtn.addEventListener('click', handleDownload);
    
    // Platform click events
    document.querySelectorAll('.platform').forEach(platform => {
        platform.addEventListener('click', handlePlatformClick);
    });
    
    // Enter key support
    videoUrl.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            playBtn.click();
        }
    });
    
    // Main Functions
    async function handlePlayClick() {
        if (videoUrl.value.trim() === '') {
            showNotification('Please enter a video URL', 'error');
            return;
        }
        
        const url = videoUrl.value.trim();
        currentVideoUrl = url;
        
        try {
            showNotification('Loading video information...', 'info');
            
            // Get video information from backend
            const response = await fetch(API_ENDPOINTS.VIDEO_INFO, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            videoInfo = data;
            
            // Reset quality selection
            selectedQuality = '';
            downloadOptions.forEach(opt => {
                opt.classList.remove('active');
                opt.classList.remove('unavailable');
                opt.style.opacity = '0.5';
                opt.style.cursor = 'not-allowed';
            });
            
            // Update available qualities
            const availableQualities = data.formats.map(f => f.quality);
            console.log('Available qualities:', availableQualities);
            
            downloadOptions.forEach(option => {
                const quality = option.getAttribute('data-quality');
                if (availableQualities.includes(quality)) {
                    option.style.opacity = '1';
                    option.style.cursor = 'pointer';
                    option.classList.remove('unavailable');
                    console.log(`Enabling quality: ${quality}`);
                } else {
                    option.style.opacity = '0.5';
                    option.style.cursor = 'not-allowed';
                    option.classList.add('unavailable');
                    console.log(`Disabling quality: ${quality}`);
                }
            });
            
            // Handle video display
            handleVideoDisplay(url, data);
            
            downloadSection.style.display = 'block';
            showNotification('Video loaded successfully! Select download quality below.', 'success');
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('Error loading video information. Please try again.', 'error');
        }
    }
    
    function handleVideoDisplay(url, data) {
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            const videoId = extractYoutubeId(url);
            if (videoId) {
                const embedUrl = `https://www.youtube.com/embed/${videoId}`;
                videoPlayer.src = embedUrl;
                videoPlayer.style.display = 'block';
                placeholder.style.display = 'none';
            }
        } else {
            // For other platforms, show thumbnail if available
            if (data.thumbnail) {
                placeholder.innerHTML = `
                    <img src="${data.thumbnail}" alt="Video Thumbnail" 
                         style="max-width: 100%; max-height: 100%; border-radius: 10px;">
                `;
            }
        }
    }
    
    async function handleDownload() {
        if (!selectedQuality) {
            showNotification('Please select a download quality', 'error');
            return;
        }
        
        if (!currentVideoUrl) {
            showNotification('No video URL found', 'error');
            return;
        }
        
        const originalText = downloadBtn.innerHTML;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        downloadBtn.disabled = true;
        
        try {
            showNotification('Starting download...', 'info');
            
            const response = await fetch(API_ENDPOINTS.DOWNLOAD, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: currentVideoUrl,
                    quality: selectedQuality
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showNotification(data.error, 'error');
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                return;
            }
            
            // Start the download
            const downloadUrl = `${config.API_BASE_URL}${data.download_path}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.click();
            
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
            showNotification('Download started! Your file will be saved shortly.', 'success');
            
        } catch (error) {
            console.error('Error:', error);
            showNotification('Error starting download. Please try again.', 'error');
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
        }
    }
    
    function handlePlatformClick() {
        const platformName = this.querySelector('.platform-name').textContent;
        videoUrl.placeholder = `Paste ${platformName} video URL here`;
        videoUrl.focus();
    }
    
    function extractYoutubeId(url) {
        let videoId = '';
        
        if (url.includes('youtube.com')) {
            videoId = url.split('v=')[1];
            const ampersandPosition = videoId.indexOf('&');
            if (ampersandPosition !== -1) {
                videoId = videoId.substring(0, ampersandPosition);
            }
        } else if (url.includes('youtu.be')) {
            videoId = url.split('/').pop();
        }
        
        return videoId;
    }
    
    function showNotification(message, type) {
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            background: ${type === 'error' ? 'linear-gradient(90deg, #ff416c, #ff4b2b)' : 
                         type === 'success' ? 'linear-gradient(90deg, #00b09b, #96c93d)' : 
                         'linear-gradient(90deg, #00c6ff, #0072ff)'};
            color: white;
            font-weight: 500;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            z-index: 1000;
            animation: slideIn 0.3s ease, fadeOut 0.5s ease 2.5s forwards;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 3000);
    }
    
    // Pre-populate with a demo URL
    videoUrl.value = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
}); 