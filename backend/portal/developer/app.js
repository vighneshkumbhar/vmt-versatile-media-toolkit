const API_BASE = 'http://localhost:8000';

// Helper: Show Error
function showError(msg, elId = 'error-banner') {
  const el = document.getElementById(elId);
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
  }
}

function clearError(elId = 'error-banner') {
  const el = document.getElementById(elId);
  if (el) el.style.display = 'none';
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (toast) {
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
  }
}

// API Wrapper
async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('vmt_access_token');
  const headers = { ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    let res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    
    if (res.status === 401 && token) {
      // Try refresh
      const refresh = localStorage.getItem('vmt_refresh_token');
      if (refresh) {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh })
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          localStorage.setItem('vmt_access_token', data.access_token);
          // Retry original
          headers['Authorization'] = `Bearer ${data.access_token}`;
          res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        } else {
          logout();
          return null;
        }
      } else {
        logout();
        return null;
      }
    }
    return res;
  } catch (err) {
    showError("Unable to connect to backend", options.errorEl || 'error-banner');
    return null;
  }
}

// Auth Handlers (index.html)
function switchTab(tab) {
  document.getElementById('tab-login').classList.remove('active');
  document.getElementById('tab-register').classList.remove('active');
  document.getElementById('login-form').style.display = 'none';
  document.getElementById('register-form').style.display = 'none';
  
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`${tab}-form`).style.display = 'block';
  clearError();
}

const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    const res = await apiCall('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (res && res.ok) {
      const data = await res.json();
      localStorage.setItem('vmt_access_token', data.access_token);
      localStorage.setItem('vmt_refresh_token', data.refresh_token);
      localStorage.setItem('vmt_username', username);
      window.location.href = 'dashboard.html';
    } else if (res) {
      showError("Invalid username or password");
    }
  });
}

const registerForm = document.getElementById('register-form');
if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();
    const email = document.getElementById('register-email').value;
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;

    if (password !== confirm) {
      return showError("Passwords do not match");
    }

    const res = await apiCall('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password })
    });

    if (res && res.ok) {
      // Auto-login
      const loginRes = await apiCall('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (loginRes && loginRes.ok) {
        const data = await loginRes.json();
        localStorage.setItem('vmt_access_token', data.access_token);
        localStorage.setItem('vmt_refresh_token', data.refresh_token);
        localStorage.setItem('vmt_username', username);
        window.location.href = 'dashboard.html';
      }
    } else if (res) {
      const err = await res.json();
      showError(err.detail || "Registration failed");
    }
  });
}

function logout() {
  apiCall('/auth/logout', { method: 'POST' }).finally(() => {
    localStorage.removeItem('vmt_access_token');
    localStorage.removeItem('vmt_refresh_token');
    localStorage.removeItem('vmt_username');
    window.location.href = 'index.html';
  });
}

// Dashboard Handlers (dashboard.html)
if (window.location.pathname.includes('dashboard.html')) {
  if (!localStorage.getItem('vmt_access_token')) {
    window.location.href = 'index.html';
  } else {
    document.getElementById('user-display').textContent = localStorage.getItem('vmt_username') || 'Developer';
    loadExtensions();
  }
}

async function loadExtensions() {
  const res = await apiCall('/developer/');
  if (res && res.ok) {
    const exts = await res.json();
    renderExtensions(exts);
  }
}

function getStatusBadge(status) {
  if (status === 'verified') return '<span class="status-badge status-verified">✓ VERIFIED</span>';
  if (status === 'rejected') return '<span class="status-badge status-rejected">✕ REJECTED</span>';
  return '<span class="status-badge status-unverified">⚠ UNVERIFIED</span>';
}

function renderExtensions(exts) {
  const container = document.getElementById('extensions-container');
  if (exts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>You haven't published any extensions yet.</p>
        <button onclick="openUploadModal()">Upload your first extension →</button>
      </div>
    `;
    return;
  }

  let html = '';
  exts.forEach(ext => {
    const rv = ext.recommended_version;
    const vStr = rv ? `v${rv.version}` : 'No versions';
    const status = rv ? rv.verification_status : 'unverified';
    
    html += `
      <div class="card" id="ext-${ext.id}">
        <div class="card-header">
          <div>
            <div class="ext-id">${ext.id}</div>
            <div class="ext-title">${ext.name}</div>
          </div>
        </div>
        <div class="ext-meta">
          ${getStatusBadge(status)} ${vStr} &nbsp;·&nbsp; ${ext.total_download_count || 0} downloads
        </div>
        <div>
          <button style="background: var(--bg-card-alt); margin-right: 0.5rem;" onclick="toggleVersions('${ext.id}')">View Versions</button>
          <button onclick="openUploadModal('${ext.id}')">Upload New Version</button>
        </div>
        <div class="versions-panel" id="versions-${ext.id}">
          <div style="color: var(--text-muted); font-size: 0.875rem;">Loading versions...</div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function toggleVersions(extId) {
  const panel = document.getElementById(`versions-${extId}`);
  if (panel.style.display === 'block') {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';

  const res = await apiCall(`/developer/${extId}/versions`);
  if (res && res.ok) {
    const versions = await res.json();
    let html = '';
    versions.forEach(v => {
      const date = new Date(v.created_at).toLocaleDateString();
      let statusStr = '';
      if (v.verification_status === 'verified') statusStr = '<span style="color: var(--success)">✓ Verified</span>';
      else if (v.verification_status === 'rejected') statusStr = '<span style="color: var(--error)">✕ Rejected</span>';
      else statusStr = '<span style="color: var(--warning)">⚠ Pending Review</span>';

      html += `
        <div class="version-row">
          <div style="font-weight: 500; width: 100px;">v${v.version}</div>
          <div style="flex: 1;">${statusStr}</div>
          <div style="color: var(--text-muted); font-size: 0.875rem;">Uploaded ${date}</div>
        </div>
      `;
      if (v.verification_status === 'rejected' && v.verification_reason) {
        html += `<div class="rejection-reason">"${v.verification_reason}"</div>`;
      }
    });
    panel.innerHTML = html || '<div style="color: var(--text-muted);">No versions found.</div>';
  } else {
    panel.innerHTML = '<div style="color: var(--error);">Failed to load versions.</div>';
  }
}

// Upload Modal
let currentUploadExtId = null;

function openUploadModal(extId = null) {
  currentUploadExtId = extId;
  document.getElementById('upload-title').textContent = extId ? 'Upload New Version' : 'Upload Extension';
  document.getElementById('ext-file').value = '';
  document.getElementById('file-info').textContent = '';
  clearError('upload-error');
  document.getElementById('upload-modal').style.display = 'flex';
}

function closeUploadModal() {
  document.getElementById('upload-modal').style.display = 'none';
}

const fileInput = document.getElementById('ext-file');
if (fileInput) {
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const sizeStr = (file.size / 1024).toFixed(1) + ' KB';
      document.getElementById('file-info').textContent = `${file.name} (${sizeStr})`;
    }
  });
}

const uploadForm = document.getElementById('upload-form');
if (uploadForm) {
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError('upload-error');
    const file = document.getElementById('ext-file').files[0];
    if (!file) return showError("Please select a file", 'upload-error');
    
    const formData = new FormData();
    formData.append('package', file); // Use the correct field name expected by the backend

    const endpoint = currentUploadExtId ? `/developer/${currentUploadExtId}/versions` : '/developer/';
    
    // Note: Do not set Content-Type header when sending FormData; browser handles it (with boundary)
    const token = localStorage.getItem('vmt_access_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      document.getElementById('upload-btn').textContent = 'Uploading...';
      document.getElementById('upload-btn').disabled = true;

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers,
        body: formData
      });

      if (res.ok) {
        closeUploadModal();
        showToast("Extension uploaded successfully");
        loadExtensions();
      } else {
        const err = await res.json();
        showError(err.detail || "Upload failed", 'upload-error');
      }
    } catch (err) {
      showError("Upload failed due to network error", 'upload-error');
    } finally {
      document.getElementById('upload-btn').textContent = 'Upload';
      document.getElementById('upload-btn').disabled = false;
    }
  });
}
