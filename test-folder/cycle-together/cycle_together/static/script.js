document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-20px)';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Confirm before leaving trip
    const leaveForms = document.querySelectorAll('form[action*="/leave"]');
    leaveForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to leave this trip?')) {
                e.preventDefault();
            }
        });
    });

    // Set minimum dates for date inputs (today)
    const today = new Date().toISOString().split('T')[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            input.setAttribute('min', today);
        }
    });

    // Validate date ranges in create/edit forms
    const startMinInput = document.getElementById('start_date_min');
    const startMaxInput = document.getElementById('start_date_max');
    
    if (startMinInput && startMaxInput) {
        startMinInput.addEventListener('change', function() {
            startMaxInput.setAttribute('min', this.value);
            if (startMaxInput.value && startMaxInput.value < this.value) {
                startMaxInput.value = this.value;
            }
        });
    }

    // Validate duration ranges
    const durationMinInput = document.getElementById('duration_days_min');
    const durationMaxInput = document.getElementById('duration_days_max');
    
    if (durationMinInput && durationMaxInput) {
        durationMinInput.addEventListener('change', function() {
            if (durationMaxInput.value && parseInt(durationMaxInput.value) < parseInt(this.value)) {
                durationMaxInput.value = this.value;
            }
        });
    }

    // Smooth scroll to messages when posting
    const messageForm = document.querySelector('.message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const tripId = window.location.pathname.match(/\/trips\/(\d+)/)[1];
            
            fetch('/trips/' + tripId + '/message', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    this.querySelector('textarea').value = '';
                    loadMessages(tripId);
                }
            })
            .catch(error => console.error('Error posting message:', error));
        });
    }

    // Highlight current nav link
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.style.color = '#667eea';
            link.style.fontWeight = '700';
        }
    });

    // Auto-refresh participant count on trip detail page (AJAX)
    if (window.location.pathname.includes('/trips/')) {
        const tripIdMatch = window.location.pathname.match(/\/trips\/(\d+)/);
        if (tripIdMatch) {
            const tripId = tripIdMatch[1];
            
            // Auto-refresh participant count every 10 seconds
            setInterval(function() {
                fetch('/trips/' + tripId + '/participants')
                    .then(response => response.json())
                    .then(data => {
                        const countElement = document.querySelector('.sidebar-section h3');
                        if (countElement && countElement.textContent.includes('Participants')) {
                            countElement.textContent = 'Participants (' + data.count + '/' + data.max + ')';
                        }
                    })
                    .catch(error => console.error('Error fetching participants:', error));
            }, 10000);
            
            // Auto-refresh messages every 3 seconds (REAL-TIME CHAT!)
            const messagesList = document.querySelector('.messages-list');
            if (messagesList) {
                setInterval(function() {
                    loadMessages(tripId);
                }, 3000); // Refresh every 3 seconds
            }
        }
    }

    // Form validation for trip creation
    const createTripForm = document.querySelector('form[action*="/create"]');
    if (createTripForm) {
        createTripForm.addEventListener('submit', function(e) {
            const startMin = document.getElementById('start_date_min').value;
            const startMax = document.getElementById('start_date_max').value;
            const durationMin = parseInt(document.getElementById('duration_days_min').value);
            const durationMax = parseInt(document.getElementById('duration_days_max').value);
            
            if (startMax < startMin) {
                e.preventDefault();
                alert('End date cannot be before start date!');
                return;
            }
            
            if (durationMax < durationMin) {
                e.preventDefault();
                alert('Maximum duration cannot be less than minimum duration!');
                return;
            }
        });
    }

    // Image preview for trip image upload
    const imageInput = document.getElementById('trip_image');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    let preview = document.getElementById('image-preview');
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = 'image-preview';
                        preview.style.maxWidth = '200px';
                        preview.style.marginTop = '10px';
                        preview.style.borderRadius = '8px';
                        imageInput.parentNode.appendChild(preview);
                    }
                    preview.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Confirm before finalizing/canceling trips
    const finalizeForms = document.querySelectorAll('form[action*="/finalize"]');
    finalizeForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to finalize this trip? No more changes will be allowed.')) {
                e.preventDefault();
            }
        });
    });

    const cancelForms = document.querySelectorAll('form[action*="/cancel"]');
    cancelForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to cancel this trip?')) {
                e.preventDefault();
            }
        });
    });

    // Auto-expand textarea as user types
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });

    // Disable submit buttons after form submission (prevent double-submit)
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains('no-disable')) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Processing...';
            }
        });
    });
});

// Function to load messages via AJAX (REAL-TIME CHAT)
function loadMessages(tripId) {
    fetch('/trips/' + tripId + '/messages')
        .then(response => response.json())
        .then(data => {
            const messagesList = document.querySelector('.messages-list');
            if (!messagesList) return;
            
            if (data.messages && data.messages.length > 0) {
                let html = '';
                data.messages.forEach(function(msg) {
                    html += '<div class="message-item">';
                    html += '<div class="message-header">';
                    html += '<a href="/user/' + msg.author_id + '" class="message-author">' + msg.author_name + '</a>';
                    html += '<span class="message-time">' + msg.timestamp + '</span>';
                    html += '</div>';
                    html += '<div class="message-text">' + msg.text + '</div>';
                    html += '</div>';
                });
                messagesList.innerHTML = html;
            } else {
                messagesList.innerHTML = '<p class="empty-messages">No messages yet. Start the conversation!</p>';
            }
        })
        .catch(error => console.error('Error loading messages:', error));
}