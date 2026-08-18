const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('token');
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...options.headers,
    },
  });

  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Request failed');
  }
  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Login failed');
  return data;
}

export async function register(payload) {
  return request('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
}

export async function getMe() {
  return request('/auth/me');
}

export async function updateUserProfile(payload) {
  return request('/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

// ── Users ─────────────────────────────────────────────────────────────────────

export async function getUsers() {
  return request('/users');
}

export async function updateUserRole(userId, role) {
  return request(`/users/${userId}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

// ── Projects ──────────────────────────────────────────────────────────────────

export async function getProjects() {
  return request('/projects');
}

export async function createProject(payload) {
  return request('/projects', { method: 'POST', body: JSON.stringify(payload) });
}

export async function updateProject(id, payload) {
  return request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function deleteProject(id) {
  return request(`/projects/${id}`, { method: 'DELETE' });
}

export async function getProjectMembers(projectId) {
  return request(`/projects/${projectId}/members`);
}

export async function addProjectMember(projectId, payload) {
  return request(`/projects/${projectId}/members`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function removeProjectMember(projectId, userId) {
  return request(`/projects/${projectId}/members/${userId}`, { method: 'DELETE' });
}

// ── Issues ────────────────────────────────────────────────────────────────────

export async function getAllIssues(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '' && v !== 'all') {
      query.append(k, v);
    }
  });
  return request(`/issues?${query.toString()}`);
}

export async function getIssues(projectId) {
  return request(`/projects/${projectId}/issues`);
}

export async function getIssueDetail(issueId) {
  return request(`/issues/${issueId}`);
}

export async function createIssue(projectId, payload) {
  return request(`/projects/${projectId}/issues`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateIssue(issueId, payload) {
  return request(`/issues/${issueId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function updateIssueStatus(issueId, status) {
  return request(`/issues/${issueId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  });
}

export async function assignIssue(issueId, assignedDeveloperId) {
  return request(`/issues/${issueId}/assign`, {
    method: 'PUT',
    body: JSON.stringify({ assigned_developer_id: assignedDeveloperId }),
  });
}

export async function deleteIssue(issueId) {
  return request(`/issues/${issueId}`, { method: 'DELETE' });
}

// ── Comments ──────────────────────────────────────────────────────────────────

export async function getComments(issueId) {
  return request(`/issues/${issueId}/comments`);
}

export async function addComment(issueId, content) {
  return request(`/issues/${issueId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function editComment(commentId, content) {
  return request(`/comments/${commentId}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function deleteComment(commentId) {
  return request(`/comments/${commentId}`, { method: 'DELETE' });
}

// ── Attachments ───────────────────────────────────────────────────────────────

export async function getAttachments(issueId) {
  return request(`/issues/${issueId}/attachments`);
}

export async function uploadAttachment(issueId, file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/issues/${issueId}/attachments`, {
    method: 'POST',
    headers: {
      ...authHeaders(),
    },
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Upload failed');
  return data;
}

export async function deleteAttachment(attachmentId) {
  return request(`/attachments/${attachmentId}`, { method: 'DELETE' });
}

// ── Sprints ───────────────────────────────────────────────────────────────────

export async function getSprints(projectId = null) {
  const path = projectId ? `/sprints?project_id=${projectId}` : '/sprints';
  return request(path);
}

export async function createSprint(projectId, payload) {
  return request(`/sprints?project_id=${projectId}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function startSprint(sprintId) {
  return request(`/sprints/${sprintId}/start`, { method: 'POST' });
}

export async function completeSprint(sprintId) {
  return request(`/sprints/${sprintId}/complete`, { method: 'POST' });
}

export async function deleteSprint(sprintId) {
  return request(`/sprints/${sprintId}`, { method: 'DELETE' });
}

// ── Dashboard & Admin ─────────────────────────────────────────────────────────

export async function getDashboardStats(projectId = null) {
  const path = projectId ? `/dashboard/stats?project_id=${projectId}` : '/dashboard/stats';
  return request(path);
}

export async function getNotifications() {
  return request('/notifications');
}

export async function markNotificationRead(id) {
  return request(`/notifications/${id}/read`, { method: 'PUT' });
}

export async function markAllNotificationsRead() {
  return request('/notifications/read-all', { method: 'PUT' });
}

export async function getAdminUsers() {
  return request('/admin/users');
}

export async function deleteAdminUser(userId) {
  return request(`/admin/users/${userId}`, { method: 'DELETE' });
}

export async function getAdminReports() {
  return request('/admin/reports');
}

// ── AI Features ───────────────────────────────────────────────────────────────

export async function aiClassifyDefect(description, title = '') {
  return request('/ai/classify-defect', {
    method: 'POST',
    body: JSON.stringify({ description, title }),
  });
}

export async function aiAssist(rawDescription) {
  return request('/ai/assist', {
    method: 'POST',
    body: JSON.stringify({ raw_description: rawDescription }),
  });
}

export async function aiPredictSeverity(title, description) {
  return request('/ai/predict-severity', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  });
}

export async function aiDetectDuplicates(projectId, title, description) {
  return request('/ai/detect-duplicates', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, title, description }),
  });
}

export async function aiSemanticSearch(query, projectId = null, threshold = 0.35, limit = 20) {
  return request('/ai/semantic-search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      project_id: projectId,
      threshold,
      limit,
    }),
  });
}

export async function aiFixCode(payload) {
  return request('/ai/fix-code', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function aiSprintHealth(sprintId) {
  return request(`/ai/sprint-health/${sprintId}`, { method: 'POST' });
}

export async function getResolutionAssistance(issueId, payload = null) {
  if (issueId) {
    return request(`/issues/${issueId}/resolution-assistance`);
  }
  return request('/ai/resolution-assistance', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ── PDF Export Downloads ──────────────────────────────────────────────────────

export async function downloadIssuePdf(issueId) {
  const token = getToken();
  const res = await fetch(`${API_BASE}/issues/${issueId}/pdf`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) throw new Error('Failed to generate defect PDF report');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `defect_report_DEF-${issueId}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadProjectPdf(projectId, projectName = 'project') {
  const token = getToken();
  const res = await fetch(`${API_BASE}/projects/${projectId}/pdf`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) throw new Error('Failed to generate project PDF summary');
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `defect_summary_${projectName.replace(/\s+/g, '_')}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export { getToken };
