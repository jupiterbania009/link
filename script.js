import config from './config.js';

// Debounce function to limit API calls
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

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const elements = {
        videoUrl: document.getElementById('videoUrl'),
        playBtn: document.getElementById('playBtn'),
        videoPlayer: document.getElementById('videoPlayer'),
        placeholder: document.getElementById('placeholder'),
        downloadSection: document.getElementById('downloadSection'),
        downloadOptions: document.querySelectorAll('.download-option'),
        downloadBtn: document.getElementById('downloadBtn')
    };

    // State management
    const state = {
        currentVideoUrl: '',
        selectedQuality: '',
        videoInfo: null,
        isProcessing: false
    };

    // API endpoints
    const API_ENDPOINTS = {
        VIDEO_INFO: `${config.API_BASE_URL}/api/video-info`,
        DOWNLOAD: `${config.API_BASE_URL}/api/download`
    };

    // Event Listeners
    elements.playBtn.addEventListener('click', handlePlayClick);
    elements.downloadBtn.addEventListener('click', handleDownload);
    elements.videoUrl.addEventListener('keypress', e => e.key === 'Enter' && elements.playBtn.click());
    
    // Optimize quality selection
    elements.downloadOptions.forEach(option => {
        option.addEventListener('click', () => handleQualitySelection(option));
    });

    document.querySelectorAll('.platform').forEach(platform => {
        platform.addEventListener('click', () => {
            const platformName = platform.querySelector('.platform-name').textContent;
            elements.videoUrl.placeholder = `Paste ${platformName} video URL here`;
            elements.videoUrl.focus();
        });
    });

    // Main Functions
    async function handlePlayClick() {
        if (state.isProcessing) return;
        
        const url = elements.videoUrl.value.trim();
        if (!url) {
            showNotification('Please enter a video URL', 'error');
            return;
        }

        state.isProcessing = true;
        elements.playBtn.disabled = true;
        showNotification('Loading video information...', 'info');

        try {
            const response = await fetch(API_ENDPOINTS.VIDEO_INFO, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();
            if (data.error) throw new Error(data.error);

            state.currentVideoUrl = url;
            state.videoInfo = data;
            updateQualityOptions(data.formats);
            handleVideoDisplay(url, data);
            
            elements.downloadSection.style.display = 'block';
            showNotification('Video loaded successfully! Select download quality below.', 'success');
        } catch (error) {
            console.error('Error:', error);
            showNotification(error.message || 'Error loading video information', 'error');
        } finally {
            state.isProcessing = false;
            elements.playBtn.disabled = false;
        }
    }

    function handleQualitySelection(option) {
        if (option.classList.contains('unavailable')) {
            showNotification('This quality is not available for the current video', 'error');
            return;
        }

        elements.downloadOptions.forEach(opt => opt.classList.remove('active'));
        option.classList.add('active');
        state.selectedQuality = option.getAttribute('data-quality');
        showNotification(`Selected quality: ${state.selectedQuality}`, 'success');
    }

    async function handleDownload() {
        if (state.isProcessing) return;
        
        if (!state.selectedQuality) {
            showNotification('Please select a download quality', 'error');
            return;
        }

        if (!state.currentVideoUrl) {
            showNotification('No video URL found', 'error');
            return;
        }

        state.isProcessing = true;
        const originalText = elements.downloadBtn.innerHTML;
        elements.downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        elements.downloadBtn.disabled = true;

        try {
            showNotification('Starting download...', 'info');
            
            const response = await fetch(API_ENDPOINTS.DOWNLOAD, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: state.currentVideoUrl,
                    quality: state.selectedQuality
                })
            });

            const data = await response.json();
            if (data.error) throw new Error(data.error);

            // Start download
            const link = document.createElement('a');
            link.href = `${config.API_BASE_URL}${data.download_path}`;
            link.click();

            showNotification('Download started! Your file will be saved shortly.', 'success');
        } catch (error) {
            console.error('Error:', error);
            showNotification(error.message || 'Error starting download', 'error');
        } finally {
            elements.downloadBtn.innerHTML = originalText;
            elements.downloadBtn.disabled = false;
            state.isProcessing = false;
        }
    }

    function handleVideoDisplay(url, data) {
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            const videoId = extractYoutubeId(url);
            if (videoId) {
                elements.videoPlayer.src = `https://www.youtube.com/embed/${videoId}`;
                elements.videoPlayer.style.display = 'block';
                elements.placeholder.style.display = 'none';
            }
        } else if (data.thumbnail) {
            elements.placeholder.innerHTML = `
                <img src="${data.thumbnail}" alt="Video Thumbnail" 
                     style="max-width: 100%; max-height: 100%; border-radius: 10px;">
            `;
        }
    }

    function updateQualityOptions(formats) {
        // Reset quality selection
        state.selectedQuality = '';
        const availableQualities = formats.map(f => f.quality);
        
        elements.downloadOptions.forEach(option => {
            const quality = option.getAttribute('data-quality');
            const isAvailable = availableQualities.includes(quality);
            
            option.classList.remove('active', 'unavailable');
            option.style.opacity = isAvailable ? '1' : '0.5';
            option.style.cursor = isAvailable ? 'pointer' : 'not-allowed';
            if (!isAvailable) option.classList.add('unavailable');
        });
    }

    function extractYoutubeId(url) {
        const match = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/);
        return match ? match[1] : null;
    }
});

// Notification system with rate limiting
const notifications = (() => {
    let timeout;
    const queue = [];
    
    function show(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '15px 25px',
            borderRadius: '10px',
            background: type === 'error' ? 'linear-gradient(90deg, #ff416c, #ff4b2b)' :
                       type === 'success' ? 'linear-gradient(90deg, #00b09b, #96c93d)' :
                       'linear-gradient(90deg, #00c6ff, #0072ff)',
            color: 'white',
            fontWeight: '500',
            boxShadow: '0 5px 15px rgba(0,0,0,0.3)',
            zIndex: '1000',
            animation: 'slideIn 0.3s ease, fadeOut 0.5s ease 2.5s forwards'
        });
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }
    
    return {
        show: (message, type) => {
            queue.push({ message, type });
            if (!timeout) {
                const process = () => {
                    if (queue.length) {
                        const { message, type } = queue.shift();
                        show(message, type);
                        timeout = setTimeout(process, 250);
                    } else {
                        timeout = null;
                    }
                };
                process();
            }
        }
    };
})();

function showNotification(message, type) {
    notifications.show(message, type);
} 
