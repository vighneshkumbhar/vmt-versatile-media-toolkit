const API_BASE = 'http://localhost:8000';

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

function getTokens() {
  return {
    access: localStorage.getItem('vmt_admin_access_token'),
    refresh: localStorage.getItem('vmt_admin_refresh_token')
  };
}

function setTokens(access, refresh) {
  localStorage.setItem('vmt_admin_access_token', access);
  localStorage.setItem('vmt_admin_refresh_token', refresh);
}

function clearTokens() {
  localStorage.removeItem('vmt_admin_access_token');
  localStorage.removeItem('vmt_admin_refresh_token');
}

function requireAuth() {
  const tokens = getTokens();
  if (!tokens.access) {
    window.location.href = 'index.html';
  }
}

async function apiCall(endpoint, options = {}) {
  const tokens = getTokens();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  if (tokens.access) {
    headers['Authorization'] = `Bearer ${tokens.access}`;
  }
  
  try {
    let response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    
    if (response.status === 401 && tokens.refresh) {
      clearTokens();
      window.location.href = 'index.html';
      return null;
    }
    
    if (response.status === 403) {
      alert("Access denied — admin account required");
      clearTokens();
      window.location.href = 'index.html';
      return null;
    }
    
    if (!response.ok) {
      throw response;
    }
    
    return await response.json();
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

// ==========================================
// LOGIN PAGE LOGIC
// ==========================================
if (window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/admin/')) {
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;
      const errorDiv = document.getElementById('login-error');
      
      try {
        const res = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        
        if (res.ok) {
          const data = await res.json();
          setTokens(data.access_token, data.refresh_token);
          localStorage.setItem('vmt_admin_username', username);
          
          // Test if admin
          const checkRes = await fetch(`${API_BASE}/admin/extensions/pending`, {
            headers: { 'Authorization': `Bearer ${data.access_token}` }
          });
          
          if (checkRes.status === 403) {
            errorDiv.textContent = "Access denied — admin account required";
            errorDiv.style.display = 'block';
            clearTokens();
          } else {
            window.location.href = 'dashboard.html';
          }
        } else {
          errorDiv.textContent = "Invalid username or password.";
          errorDiv.style.display = 'block';
        }
      } catch (err) {
        errorDiv.textContent = "Network error. Is the backend running?";
        errorDiv.style.display = 'block';
      }
    });
  }
}

// ==========================================
// DASHBOARD LOGIC
// ==========================================
if (window.location.pathname.endsWith('dashboard.html')) {
  requireAuth();
  
  document.getElementById('current-username').textContent = localStorage.getItem('vmt_admin_username') || 'Admin';
  
  document.getElementById('logout-btn').addEventListener('click', () => {
    clearTokens();
    window.location.href = 'index.html';
  });
  
  // Navigation
  const navItems = document.querySelectorAll('.nav-item');
  const views = document.querySelectorAll('.view');
  
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(nav => nav.classList.remove('active'));
      item.classList.add('active');
      
      const viewId = `view-${item.dataset.view}`;
      views.forEach(view => {
        if (view.id === viewId) {
          view.classList.add('active');
        } else {
          view.classList.remove('active');
        }
      });
      
      if (item.dataset.view === 'pending') loadPending();
      if (item.dataset.view === 'all') loadAllExtensions();
    });
  });
  
  let currentReviewExtId = null;
  let currentReviewVer = null;
  
  async function loadPending() {
    try {
      const list = document.getElementById('pending-list');
      list.innerHTML = 'Loading...';
      const pending = await apiCall('/admin/extensions/pending');
      
      const badge = document.getElementById('pending-badge');
      if (pending.length > 0) {
        badge.textContent = pending.length;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
      
      if (pending.length === 0) {
        list.innerHTML = '<p style="color: var(--text-dim)">No pending extensions to review.</p>';
        return;
      }
      
      list.innerHTML = '';
      pending.forEach(item => {
        const card = document.createElement('div');
        card.className = 'ext-card';
        
        let permsHtml = item.permissions && item.permissions.length > 0 
          ? item.permissions.map(p => `<span class="perm-tag">· ${p}</span>`).join('') 
          : '<span style="color: var(--text-muted)">None</span>';
          
        card.innerHTML = `
          <div class="ext-card-header">
            <div>
              <div class="ext-id">${item.extension_id}</div>
              <div class="ext-title">Version ${item.version}</div>
              <div class="ext-meta">Submitted ${new Date(item.created_at).toLocaleString()}</div>
            </div>
            <button class="primary" onclick="openReview('${item.extension_id}', '${item.version}')">Review &rarr;</button>
          </div>
          <div style="margin-top: 8px;">
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">Capabilities requested:</div>
            <div class="permissions">${permsHtml}</div>
          </div>
        `;
        list.appendChild(card);
      });
    } catch (e) {
      document.getElementById('pending-list').innerHTML = 'Failed to load pending extensions.';
    }
  }
  
  window.openReview = async function(extId, versionStr) {
    const panel = document.getElementById('review-panel');
    const content = document.getElementById('review-content');
    content.innerHTML = 'Loading...';
    panel.classList.add('open');
    
    currentReviewExtId = extId;
    currentReviewVer = versionStr;
    
    try {
      const ext = await apiCall(`/extensions/${extId}`);
      const verObj = ext.versions.find(v => v.version === versionStr);
      
      if (!verObj) throw new Error("Version not found in details");
      
      let permsHtml = verObj.permissions && verObj.permissions.length > 0
        ? verObj.permissions.map(p => `<div class="perm-tag" style="margin-bottom: 8px; display: inline-block;">⚠ ${p}</div>`).join(' ')
        : 'None';
        
      let historyHtml = ext.versions.map(v => {
        let statusIcon = '';
        let color = '';
        if (v.verification_status === 'verified') { statusIcon = '✓ Verified'; color = 'var(--success)'; }
        else if (v.verification_status === 'unverified') { statusIcon = '⚠ Pending'; color = 'var(--warning)'; }
        else { statusIcon = '✕ Rejected'; color = 'var(--error)'; }
        
        const isCurrent = v.version === versionStr ? '(this version)' : '';
        return `<div><span style="display:inline-block; width: 60px;">v${v.version}</span> <span style="color: ${color}">${statusIcon} ${isCurrent}</span></div>`;
      }).join('');
      
      content.innerHTML = `
        <div class="review-header">
          <h1 style="margin: 0 0 8px 0;">${ext.name} <span style="color: var(--text-muted); font-size: 1.2rem; font-weight: normal;">v${verObj.version}</span></h1>
          <div style="color: var(--text-muted);">
            ID: ${ext.id} · by ${ext.author} · Submitted ${new Date(verObj.created_at).toLocaleString()}
          </div>
        </div>
        
        <div class="review-section">
          <h3>Description</h3>
          <p>${ext.description}</p>
        </div>
        
        <div class="review-section">
          <h3>Capabilities Requested</h3>
          <div>${permsHtml}</div>
        </div>
        
        <div class="review-section">
          <h3>Compatibility</h3>
          <p>VMT >= ${verObj.min_vmt_version}</p>
        </div>
        
        <div class="review-section">
          <h3>Changelog</h3>
          <p>${verObj.changelog || 'No changelog provided.'}</p>
        </div>
        
        <div class="review-section">
          <h3>Version History</h3>
          <div style="font-family: monospace; background: var(--bg-card); padding: 16px; border-radius: 4px; border: 1px solid var(--border);">
            ${historyHtml}
          </div>
        </div>
        
        <div class="decision-box">
          <h3 style="margin-top: 0;">DECISION</h3>
          <div class="decision-actions">
            <button class="success" onclick="verifyVersion()">✓ VERIFY</button>
            <button class="danger" onclick="toggleRejectReason()">✕ REJECT</button>
          </div>
          
          <div id="reject-reason-box" class="reject-reason">
            <label style="display: block; margin-bottom: 8px; color: var(--text-muted);">Rejection reason (required):</label>
            <textarea id="reject-reason-text" rows="3" placeholder="Explain why this version is being rejected..."></textarea>
            <button class="danger" style="margin-top: 8px;" onclick="rejectVersion()">Submit Rejection</button>
          </div>
        </div>
      `;
    } catch (e) {
      content.innerHTML = 'Error loading extension details.';
    }
  };
  
  document.getElementById('close-review').addEventListener('click', () => {
    document.getElementById('review-panel').classList.remove('open');
    currentReviewExtId = null;
    currentReviewVer = null;
  });
  
  window.toggleRejectReason = function() {
    document.getElementById('reject-reason-box').classList.toggle('open');
  };
  
  window.verifyVersion = async function() {
    if (!currentReviewExtId || !currentReviewVer) return;
    try {
      await apiCall(`/admin/extensions/${currentReviewExtId}/versions/${currentReviewVer}/verify`, {
        method: 'POST'
      });
      showToast('✓ Version verified');
      document.getElementById('review-panel').classList.remove('open');
      loadPending();
    } catch (e) {
      showToast('Error verifying version', 'error');
    }
  };
  
  window.rejectVersion = async function() {
    if (!currentReviewExtId || !currentReviewVer) return;
    const reason = document.getElementById('reject-reason-text').value.trim();
    if (!reason) {
      showToast('Please provide a rejection reason.', 'error');
      return;
    }
    
    try {
      await apiCall(`/admin/extensions/${currentReviewExtId}/versions/${currentReviewVer}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast('Version rejected', 'warning');
      document.getElementById('review-panel').classList.remove('open');
      loadPending();
    } catch (e) {
      showToast('Error rejecting version', 'error');
    }
  };
  
  async function loadAllExtensions() {
    try {
      const list = document.getElementById('all-ext-list');
      list.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
      const exts = await apiCall('/extensions/');
      
      list.innerHTML = '';
      exts.forEach(ext => {
        let statusStr = 'Unknown';
        let statusClass = '';
        if (ext.is_disabled) {
          statusStr = 'DISABLED';
          statusClass = 'status-disabled';
        } else if (ext.recommended_version) {
          statusStr = 'Active';
          statusClass = 'status-verified';
        } else {
          statusStr = 'No Verified Version';
          statusClass = 'status-unverified';
        }
        
        let actions = '';
        if (ext.is_disabled) {
          actions = `<button disabled>Enable (n/a)</button>`;
        } else {
          actions = `<button class="danger" onclick="disableExtension('${ext.id}')">Disable</button>`;
        }
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-family: monospace;">${ext.id}</td>
          <td>${ext.name}</td>
          <td><span class="status-badge ${statusClass}">${statusStr}</span></td>
          <td>${ext.total_download_count || 0}</td>
          <td>${actions}</td>
        `;
        list.appendChild(tr);
      });
    } catch (e) {
      document.getElementById('all-ext-list').innerHTML = '<tr><td colspan="5">Error loading extensions.</td></tr>';
    }
  }
  
  window.disableExtension = async function(extId) {
    if (!confirm(`Are you sure you want to disable ${extId}?`)) return;
    try {
      await apiCall(`/admin/extensions/${extId}/disable`, {
        method: 'POST'
      });
      showToast('Extension disabled');
      loadAllExtensions();
    } catch (e) {
      showToast('Error disabling extension', 'error');
    }
  };

  // Init
  loadPending();
}
