// frontend/script.js
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileInput');
const artwork = document.getElementById('artwork');
const trackTitle = document.getElementById('trackTitle');
const trackArtist = document.getElementById('trackArtist');
const audioPlayer = document.getElementById('audioPlayer');
const resultsDiv = document.getElementById('results');

// Prevent default drag behaviors
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Highlight drop area when dragging over it
['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropArea.classList.add('active');
}

function unhighlight(e) {
    dropArea.classList.remove('active');
}

// Handle drop
dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;
    handleFiles(files);
}

// Handle file selection from input
fileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/recognize', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            if (response.status === 404) {
                alert("Track not recognized.  Try a different audio file.");
            } else if (response.status === 500){
                alert("An error occurred on the server.");
            }
            else{
              alert(`Error: ${response.status} - ${response.statusText}`);
            }
            return;
        }

        const data = await response.json();

        if (data) {
            displayResults(data);
        } else {
            alert('No results found.');
        }

    } catch (error) {
        console.error('Error during upload:', error);
        alert('An error occurred during the upload.');
    }
}

function displayResults(data) {
    artwork.src = data.artwork_url || ''; // Use provided artwork or fallback
    trackTitle.textContent = data.title || 'Unknown Title';
    trackArtist.textContent = data.artist || 'Unknown Artist';
    resultsDiv.style.display = 'block';

    if (data.stream_url) {
        audioPlayer.src = data.stream_url;
        audioPlayer.style.display = 'block';  // Ensure audio player is shown if a stream URL exists.
    } else {
        audioPlayer.src = ''; // Clear the source if there's no stream
        audioPlayer.style.display = 'none';  // Hide the audio player if no stream
        alert("No stream URL available.");
    }
}