// Main JavaScript for Student Grievance Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // File upload handler
    const fileUploadAreas = document.querySelectorAll('.file-upload-area');
    fileUploadAreas.forEach(area => {
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('dragover');
        });

        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
        });

        area.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            handleFileUpload(e.dataTransfer.files);
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Search functionality
    const searchInput = document.querySelector('#search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            performSearch(this.value);
        }, 300));
    }

    // Status update confirmation
    const statusUpdateButtons = document.querySelectorAll('.status-update-btn');
    statusUpdateButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const status = this.dataset.status;
            const grievanceId = this.dataset.grievanceId;
            
            if (confirm(`Are you sure you want to change the status to ${status}?`)) {
                updateGrievanceStatus(grievanceId, status);
            }
        });
    });

    // Real-time comment updates
    initializeCommentSystem();
});

// File upload handler
function handleFileUpload(files) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain'];

    Array.from(files).forEach(file => {
        if (file.size > maxSize) {
            showAlert('error', 'File size must be less than 10MB');
            return;
        }

        if (!allowedTypes.includes(file.type)) {
            showAlert('error', 'File type not allowed');
            return;
        }

        // Add file to upload queue
        addFileToUploadQueue(file);
    });
}

// Add file to upload queue
function addFileToUploadQueue(file) {
    const fileList = document.querySelector('#file-list');
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item d-flex justify-content-between align-items-center p-2 border rounded mb-2';
    fileItem.innerHTML = `
        <div>
            <i class="fas fa-file"></i>
            <span>${file.name}</span>
            <small class="text-muted">(${formatFileSize(file.size)})</small>
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(this)">
            <i class="fas fa-times"></i>
        </button>
    `;
    fileList.appendChild(fileItem);
}

// Remove file from upload queue
function removeFile(button) {
    button.closest('.file-item').remove();
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Debounce function
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Perform search
function performSearch(query) {
    if (query.length < 3) return;

    fetch(`/api/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

// Display search results
function displaySearchResults(results) {
    const searchResults = document.querySelector('#search-results');
    searchResults.innerHTML = '';

    if (results.length === 0) {
        searchResults.innerHTML = '<p>No results found</p>';
        return;
    }

    results.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item p-3 border-bottom';
        resultItem.innerHTML = `
            <h6><a href="${result.url}">${result.title}</a></h6>
            <p class="text-muted">${result.description}</p>
            <small class="text-muted">Category: ${result.category}</small>
        `;
        searchResults.appendChild(resultItem);
    });
}

// Update grievance status
function updateGrievanceStatus(grievanceId, status) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch(`/api/grievances/${grievanceId}/status/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', 'Status updated successfully');
            location.reload();
        } else {
            showAlert('error', 'Failed to update status');
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showAlert('error', 'An error occurred while updating status');
    });
}

// Initialize comment system
function initializeCommentSystem() {
    const commentForm = document.querySelector('#comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitComment();
        });
    }

    // Auto-refresh comments every 30 seconds
    setInterval(refreshComments, 30000);
}

// Submit comment
function submitComment() {
    const form = document.querySelector('#comment-form');
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            form.reset();
            refreshComments();
            showAlert('success', 'Comment submitted successfully');
        } else {
            showAlert('error', 'Failed to submit comment');
        }
    })
    .catch(error => {
        console.error('Error submitting comment:', error);
        showAlert('error', 'An error occurred while submitting comment');
    });
}

// Refresh comments
function refreshComments() {
    const commentThread = document.querySelector('#comment-thread');
    if (!commentThread) return;

    const grievanceId = commentThread.dataset.grievanceId;
    
    fetch(`/api/grievances/${grievanceId}/comments/`)
        .then(response => response.json())
        .then(data => {
            updateCommentThread(data.comments);
        })
        .catch(error => {
            console.error('Error refreshing comments:', error);
        });
}

// Update comment thread
function updateCommentThread(comments) {
    const commentThread = document.querySelector('#comment-thread');
    commentThread.innerHTML = '';

    comments.forEach(comment => {
        const commentItem = document.createElement('div');
        commentItem.className = `comment-item ${comment.is_admin ? 'admin' : 'student'}`;
        commentItem.innerHTML = `
            <div class="comment-meta">
                <strong>${comment.user_name}</strong>
                <span class="text-muted">${comment.timestamp}</span>
            </div>
            <div class="comment-content">${comment.message}</div>
        `;
        commentThread.appendChild(commentItem);
    });

    // Scroll to bottom
    commentThread.scrollTop = commentThread.scrollHeight;
}

// Show alert
function showAlert(type, message) {
    const alertContainer = document.querySelector('#alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.appendChild(alert);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Export functions for global use
window.GrievanceSystem = {
    showAlert,
    updateGrievanceStatus,
    handleFileUpload,
    performSearch
};
