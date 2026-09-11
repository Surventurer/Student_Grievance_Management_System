// Main JavaScript for Student Grievance Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize responsive features
    initializeResponsiveFeatures();
    
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
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        });
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

// RESPONSIVE FEATURES INITIALIZATION
function initializeResponsiveFeatures() {
    // Handle mobile dropdown positioning
    handleMobileDropdowns();
    
    // Initialize responsive tables
    initializeResponsiveTables();
    
    // Handle mobile navigation
    initializeMobileNavigation();
    
    // Handle touch events for mobile
    initializeTouchEvents();
    
    // Handle window resize events
    window.addEventListener('resize', handleWindowResize);
    
    // Initial responsive check
    handleWindowResize();
}

// Handle mobile dropdown positioning
function handleMobileDropdowns() {
    // Let Bootstrap 5 handle positioning natively
}

// Initialize responsive tables
function initializeResponsiveTables() {
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        // Add horizontal scroll indicators on mobile
        if (window.innerWidth <= 768) {
            const wrapper = table.closest('.table-responsive');
            if (wrapper) {
                wrapper.addEventListener('scroll', function() {
                    const scrollLeft = this.scrollLeft;
                    const scrollWidth = this.scrollWidth;
                    const clientWidth = this.clientWidth;
                    
                    // Add visual indicators for scrollable content
                    if (scrollLeft > 0) {
                        this.classList.add('scroll-left');
                    } else {
                        this.classList.remove('scroll-left');
                    }
                    
                    if (scrollLeft < scrollWidth - clientWidth - 1) {
                        this.classList.add('scroll-right');
                    } else {
                        this.classList.remove('scroll-right');
                    }
                });
            }
        }
    });
}

// Initialize mobile navigation
function initializeMobileNavigation() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 992 && 
                !navbarToggler.contains(e.target) && 
                !navbarCollapse.contains(e.target) && 
                navbarCollapse.classList.contains('show')) {
                
                const collapseInstance = bootstrap.Collapse.getInstance(navbarCollapse);
                if (collapseInstance) {
                    collapseInstance.hide();
                }
            }
        });
        
        // Close mobile menu when clicking on a nav link
        const navLinks = navbarCollapse.querySelectorAll('.nav-link:not(.dropdown-toggle)');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 992) {
                    const collapseInstance = bootstrap.Collapse.getInstance(navbarCollapse);
                    if (collapseInstance) {
                        collapseInstance.hide();
                    }
                }
            });
        });
    }
}

// Initialize touch events for mobile
function initializeTouchEvents() {
    // Add swipe gesture for mobile navigation
    let touchStartX = 0;
    let touchStartY = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    });
    
    document.addEventListener('touchend', function(e) {
        if (window.innerWidth <= 768) {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            
            // Horizontal swipe detection
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    // Swipe right - could trigger back navigation or drawer open
                    handleSwipeRight();
                } else {
                    // Swipe left - could trigger forward navigation or drawer close
                    handleSwipeLeft();
                }
            }
        }
    });
}

// Handle window resize events
function handleWindowResize() {
    const width = window.innerWidth;
    
    // Adjust card layouts
    adjustCardLayouts(width);
    
    // Adjust table displays
    adjustTableDisplays(width);
    
    // Adjust modal sizes
    adjustModalSizes(width);
    
    // Update navigation state
    updateNavigationState(width);
}

// Adjust card layouts based on screen size
function adjustCardLayouts(width) {
    const dashboardCards = document.querySelectorAll('.dashboard-card');
    dashboardCards.forEach(card => {
        if (width <= 576) {
            card.classList.add('mobile-card');
        } else {
            card.classList.remove('mobile-card');
        }
    });
}

// Adjust table displays
function adjustTableDisplays(width) {
    const responsiveTables = document.querySelectorAll('.table-responsive');
    responsiveTables.forEach(table => {
        if (width <= 768) {
            table.style.fontSize = '0.875rem';
        } else {
            table.style.fontSize = '';
        }
    });
}

// Adjust modal sizes
function adjustModalSizes(width) {
    const modals = document.querySelectorAll('.modal-dialog');
    modals.forEach(modal => {
        if (width <= 576) {
            modal.classList.add('modal-fullscreen-sm-down');
        } else {
            modal.classList.remove('modal-fullscreen-sm-down');
        }
    });
}

// Update navigation state
function updateNavigationState(width) {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        if (width <= 992) {
            navbar.classList.add('mobile-nav');
        } else {
            navbar.classList.remove('mobile-nav');
        }
    }
}

// Handle swipe gestures
function handleSwipeRight() {
    // Could implement drawer opening or back navigation
    console.log('Swipe right detected');
}

function handleSwipeLeft() {
    // Could implement drawer closing or forward navigation
    console.log('Swipe left detected');
}

// Touch-friendly button size adjustment
function adjustTouchTargets() {
    if ('ontouchstart' in window) {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => {
            btn.style.minHeight = '44px';
            btn.style.minWidth = '44px';
        });
    }
}

// Initialize touch targets on load
document.addEventListener('DOMContentLoaded', adjustTouchTargets);

// Export functions for global use
window.GrievanceSystem = {
    showAlert,
    updateGrievanceStatus,
    handleFileUpload,
    initializeResponsiveFeatures,
    handleWindowResize
};
