with open("src/templates/admin_panel/grievance_detail.html", "r") as f:
    content = f.read()
    
# We need to make sure adminCommentsUrl, escapeHtml, and renderAdminComments are defined BEFORE loadInitialThread.
insert_idx = content.find("function loadInitialThread()")
js_funcs = """
const adminCommentsUrl = '{% url "grievances:grievance_comments" grievance.id %}';

function escapeHtml(value) {
    if (!value) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function renderAdminComments(comments) {
    const container = document.getElementById('adminChatContainer');
    if (!container) return;

    if (!comments.length) {
        container.innerHTML = `
            <div class="mb-4">
                <h6 class="fw-bold mb-3">Previous Comments:</h6>
                <div class="text-center text-muted py-4">
                    <i class="fas fa-comments fa-3x mb-3 text-secondary"></i>
                    <p class="mb-0">No comments or responses yet. Start the conversation below!</p>
                </div>
            </div>`;
        return;
    }

    const html = comments.map(comment => `
        <div class="comment-box mb-3 ${comment.is_internal ? 'border-warning' : ''}">
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                    <strong>
                        ${comment.is_student
                            ? '<i class="fas fa-user me-1 text-primary"></i>' + escapeHtml(comment.user) + ' (Student)'
                            : '<i class="fas fa-user-shield me-1 text-success"></i>' + escapeHtml(comment.user) + ' (Admin)'}
                    </strong>
                    ${comment.comment_type !== 'comment' ? `<span class="badge bg-${comment.comment_type === 'status_update' ? 'info' : 'secondary'} ms-2">${escapeHtml(comment.comment_type.replace('_', ' '))}</span>` : ''}
                    ${comment.is_internal ? '<span class="badge bg-warning ms-1">Internal</span>' : ''}
                </div>
                <small class="text-muted">${new Date(comment.timestamp).toLocaleString()}</small>
            </div>
            <p class="mb-0">${escapeHtml(comment.message).replace(/\\n/g, '<br>')}</p>
        </div>
    `).join('');

    container.innerHTML = `
        <h6 class="fw-bold mb-3">Previous Comments:</h6>
        ${html}`;
}

"""
new_content = content[:insert_idx] + js_funcs + content[insert_idx:]
with open("src/templates/admin_panel/grievance_detail.html", "w") as f:
    f.write(new_content)
