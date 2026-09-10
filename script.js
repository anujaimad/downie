/*
  Application: DOWNIE
  Developed by: 1mad
  100% Copyrights to 1mad. All rights reserved.
*/
const urlInput = document.getElementById('url-input');
const fetchBtn = document.getElementById('fetch-btn');
const loadingIndicator = document.getElementById('loading');
const mediaCard = document.getElementById('media-card');
const mediaThumbnail = document.getElementById('media-thumbnail');
const mediaTitle = document.getElementById('media-title');
const downloadBtn = document.getElementById('download-btn');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const saveFileBtn = document.getElementById('save-file-btn');
const formatPills = document.getElementById('format-pills');
const carouselTrack = document.getElementById('format-carousel');
const carouselItems = document.querySelectorAll('.carousel-item');

let selectedQuality = '720p'; // Default selection
let currentUrl = null;
let progressInterval = null;

// Initialize state
downloadBtn.disabled = false;

function updateCarousel() {
    if (!carouselTrack) return;
    const trackCenter = carouselTrack.scrollLeft + carouselTrack.clientWidth / 2;
    let minDiff = Infinity;
    let activeItem = null;

    carouselItems.forEach(item => {
        const itemCenter = item.offsetLeft + item.clientWidth / 2;
        const diff = Math.abs(trackCenter - itemCenter);
        if (diff < minDiff) {
            minDiff = diff;
            activeItem = item;
        }
    });

    if (activeItem) {
        carouselItems.forEach(i => i.classList.remove('active'));
        activeItem.classList.add('active');
        selectedQuality = activeItem.dataset.quality;
    }
}

if (carouselTrack) {
    carouselTrack.addEventListener('scroll', updateCarousel);
    carouselItems.forEach(item => {
        item.addEventListener('click', () => {
            const scrollPos = item.offsetLeft - carouselTrack.clientWidth / 2 + item.clientWidth / 2;
            carouselTrack.scrollTo({ left: scrollPos, behavior: 'smooth' });
        });
    });
    setTimeout(() => {
        if (carouselItems[2]) {
            const scrollPos = carouselItems[2].offsetLeft - carouselTrack.clientWidth / 2 + carouselItems[2].clientWidth / 2;
            carouselTrack.scrollTo({ left: scrollPos, behavior: 'instant' });
        }
        updateCarousel();
    }, 50);
}

urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        fetchBtn.click();
    }
});

fetchBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return alert('Please enter a URL');

    currentUrl = url;
    
    // Reset UI
    mediaCard.classList.add('hidden');
    progressContainer.classList.add('hidden');
    saveFileBtn.classList.add('hidden');
    downloadBtn.disabled = true;
    downloadBtn.classList.remove('hidden');
    formatPills.classList.remove('hidden');
    
    selectedQuality = '720p';
    downloadBtn.disabled = false;
    
    if (progressInterval) clearInterval(progressInterval);
    
    loadingIndicator.classList.remove('hidden');

    try {
        const response = await fetch('http://127.0.0.1:5000/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            mediaThumbnail.src = data.thumbnail || 'https://via.placeholder.com/400x225?text=No+Thumbnail';
            mediaTitle.textContent = data.title;
            mediaTitle.title = data.title;
            
            loadingIndicator.classList.add('hidden');
            mediaCard.classList.remove('hidden');
            
            // Snap to 720p after the card is visible and DOM layout is calculated
            setTimeout(() => {
                if (carouselTrack && carouselItems[2]) {
                    const scrollPos = carouselItems[2].offsetLeft - carouselTrack.clientWidth / 2 + carouselItems[2].clientWidth / 2;
                    carouselTrack.scrollTo({ left: scrollPos, behavior: 'instant' });
                    updateCarousel();
                }
            }, 50);
        } else {
            alert(data.error || 'Failed to fetch media info');
            loadingIndicator.classList.add('hidden');
        }
    } catch (err) {
        alert('An error occurred while fetching information: ' + err.message);
        loadingIndicator.classList.add('hidden');
        console.error(err);
    }
});

downloadBtn.addEventListener('click', async () => {
    if (!selectedQuality || !currentUrl) return;
    
    downloadBtn.classList.add('hidden');
    formatPills.classList.add('hidden');
    progressContainer.classList.remove('hidden');
    
    progressFill.style.width = '0%';
    progressFill.style.background = 'var(--green-gradient)';
    progressText.textContent = '0%';
    progressText.style.opacity = '0';
    saveFileBtn.classList.add('hidden');
    
    try {
        const response = await fetch('http://127.0.0.1:5000/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                url: currentUrl, 
                quality: selectedQuality 
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const downloadId = data.download_id;
            progressInterval = setInterval(() => checkProgress(downloadId), 1000);
        } else {
            alert(data.error || 'Failed to start download');
            downloadBtn.classList.remove('hidden');
            formatPills.classList.remove('hidden');
            progressContainer.classList.add('hidden');
        }
    } catch (err) {
        alert('An error occurred.');
        console.error(err);
        downloadBtn.classList.remove('hidden');
        formatPills.classList.remove('hidden');
        progressContainer.classList.add('hidden');
    }
});

async function checkProgress(downloadId) {
    const progressSpeed = document.getElementById('progressSpeed');

    try {
        const response = await fetch(`/api/progress/${downloadId}`);
        const data = await response.json();
        
        if (response.ok) {
            if (data.status === 'downloading' || data.status === 'starting') {
                const pctStr = data.progress.replace('%', '').trim();
                const pct = parseFloat(pctStr);
                if (!isNaN(pct)) {
                    progressFill.style.width = `${Math.max(pct, 10)}%`;
                    progressText.textContent = data.progress;
                    progressText.style.opacity = '1';
                }
                
                if (data.speed && progressSpeed) {
                    progressSpeed.textContent = data.speed;
                }
            } else if (data.status === 'completed') {
                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                progressText.textContent = 'Done';
                progressText.style.opacity = '1';
                
                if (progressSpeed) progressSpeed.textContent = "Complete!";
                
                if (typeof confetti === 'function') {
                    confetti({
                        particleCount: 150,
                        spread: 80,
                        origin: { y: 0.6 }
                    });
                }
                
                saveFileBtn.href = `/api/file/${downloadId}`;
                saveFileBtn.classList.remove('hidden');
            } else if (data.status === 'error') {
                clearInterval(progressInterval);
                progressText.textContent = 'Error';
                progressText.style.opacity = '1';
                progressFill.style.background = '#EF4444'; // Red error color
                if (progressSpeed) progressSpeed.textContent = "Failed";
            }
        }
    } catch (err) {
        console.error('Error checking progress:', err);
    }
}
