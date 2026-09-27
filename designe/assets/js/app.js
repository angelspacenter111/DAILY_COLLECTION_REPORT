/* --- PDF-to-Excel Data Processing Admin Dashboard - Core Application Logic (MPA Version) --- */

// 1. STATE INITIALIZATION (Local Storage Persistent)
const DEFAULT_STATE = {
  theme: 'light',
  files: [
    { id: 'F-101', name: 'invoice_fedex_9021.pdf', category: 'Invoice', date: '2026-07-10 10:14', status: 'Completed', recordsCount: 1, size: '420 KB', duration: '1.4s' },
    { id: 'F-102', name: 'hotel_receipt_july.pdf', category: 'Receipt', date: '2026-07-10 11:45', status: 'Completed', recordsCount: 1, size: '1.2 MB', duration: '1.2s' },
    { id: 'F-103', name: 'q2_earnings_tables.pdf', category: 'Report', date: '2026-07-11 09:30', status: 'Completed', recordsCount: 4, size: '8.4 MB', duration: '2.5s' },
    { id: 'F-104', name: 'bank_stmt_june2026.pdf', category: 'Bank Statement', date: '2026-07-11 16:22', status: 'Completed', recordsCount: 6, size: '2.1 MB', duration: '1.9s' },
    { id: 'F-105', name: 'acme_sales_contract.pdf', category: 'Contract', date: '2026-07-12 11:05', status: 'Failed', recordsCount: 0, size: '512 KB', duration: '0.8s' }
  ],
  records: [
    { id: 'REC-001', fileId: 'F-101', fileName: 'invoice_fedex_9021.pdf', invoiceNum: 'FDX-99812A', customer: 'Federal Express Corp', date: '2026-07-08', amount: 342.50, tax: 27.40, status: 'Valid' },
    { id: 'REC-002', fileId: 'F-102', fileName: 'hotel_receipt_july.pdf', invoiceNum: 'HTL-882199', customer: 'Grand Hyatt Seattle', date: '2026-07-09', amount: 890.00, tax: 89.00, status: 'Valid' },
    { id: 'REC-003', fileId: 'F-103', fileName: 'q2_earnings_tables.pdf', invoiceNum: 'Q2-ACME-01', customer: 'ACME Technologies LLC', date: '2026-06-30', amount: 15400.00, tax: 0.00, status: 'Review' },
    { id: 'REC-004', fileId: 'F-103', fileName: 'q2_earnings_tables.pdf', invoiceNum: 'Q2-ACME-02', customer: 'ACME Technologies LLC', date: '2026-06-30', amount: 4800.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-005', fileId: 'F-103', fileName: 'q2_earnings_tables.pdf', invoiceNum: 'Q2-ACME-03', customer: 'ACME Technologies LLC', date: '2026-06-30', amount: 12500.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-006', fileId: 'F-103', fileName: 'q2_earnings_tables.pdf', invoiceNum: 'Q2-ACME-04', customer: 'ACME Technologies LLC', date: '2026-06-30', amount: 7300.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-007', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-01', customer: 'Chase Business Acct', date: '2026-06-01', amount: -1500.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-008', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-02', customer: 'Chase Business Acct', date: '2026-06-05', amount: 5430.20, tax: 0.00, status: 'Valid' },
    { id: 'REC-009', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-03', customer: 'Chase Business Acct', date: '2026-06-12', amount: -245.90, tax: 0.00, status: 'Review' },
    { id: 'REC-010', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-04', customer: 'Chase Business Acct', date: '2026-06-15', amount: 3200.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-011', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-05', customer: 'Chase Business Acct', date: '2026-06-20', amount: -110.00, tax: 0.00, status: 'Valid' },
    { id: 'REC-012', fileId: 'F-104', fileName: 'bank_stmt_june2026.pdf', invoiceNum: 'STMT-JUN26-06', customer: 'Chase Business Acct', date: '2026-06-28', amount: 4890.10, tax: 0.00, status: 'Valid' }
  ],
  logs: [
    { timestamp: '2026-07-12 11:06', user: 'Sarah Connor', module: 'Queue', action: 'Extraction Failure', status: 'Error', details: 'Failed to extract key-value schema on acme_sales_contract.pdf. Signature mismatch.' },
    { timestamp: '2026-07-12 11:05', user: 'Sarah Connor', module: 'Upload', action: 'Upload Successful', status: 'Success', details: 'Uploaded acme_sales_contract.pdf (512 KB).' },
    { timestamp: '2026-07-11 16:25', user: 'Markus Wright', module: 'Excel', action: 'Excel Schema Append', status: 'Success', details: 'Appended 6 records from bank_stmt_june2026.pdf into master Excel.' },
    { timestamp: '2026-07-11 16:22', user: 'Markus Wright', module: 'Parser', action: 'OCR Parsing Completed', status: 'Success', details: 'Parsed bank_stmt_june2026.pdf with 100% OCR compliance.' },
    { timestamp: '2026-07-11 09:33', user: 'John Connor', module: 'Excel', action: 'Dataset Created', status: 'Success', details: 'Created sheet schema for q2_earnings_tables.pdf.' },
    { timestamp: '2026-07-11 09:30', user: 'John Connor', module: 'Upload', action: 'Upload Successful', status: 'Success', details: 'Uploaded q2_earnings_tables.pdf (8.4 MB).' },
    { timestamp: '2026-07-10 11:47', user: 'Sarah Connor', module: 'Parser', action: 'OCR Parsing Completed', status: 'Success', details: 'Parsed hotel_receipt_july.pdf (1 record).' },
    { timestamp: '2026-07-10 10:15', user: 'Sarah Connor', module: 'Excel', action: 'Excel Downloaded', status: 'Success', details: 'Downloaded master dataset (12 records).' }
  ],
  users: [
    { name: 'Sarah Connor', email: 'sarah.c@aerodata.io', role: 'Super Admin', status: 'Active', active: 'Active Now', permissions: 'Full Access (Org Owner)', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80' },
    { name: 'John Connor', email: 'john.c@aerodata.io', role: 'Admin', status: 'Active', active: '2 hours ago', permissions: 'Full Read/Write, Queue Manage', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&q=80' },
    { name: 'Markus Wright', email: 'markus.w@aerodata.io', role: 'Manager', status: 'Active', active: '1 day ago', permissions: 'PDF Upload, Process Only', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=100&q=80' },
    { name: 'Kate Connor', email: 'kate.c@aerodata.io', role: 'Viewer', status: 'Inactive', active: '3 weeks ago', permissions: 'Read-only Access', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&q=80' }
  ],
  notifications: [
    { id: 1, text: 'acme_sales_contract.pdf failed to parse correctly', time: '5m ago', type: 'error' },
    { id: 2, text: '6 records appended from bank_stmt_june2026.pdf', time: '1h ago', type: 'success' }
  ],
  settings: {
    orgName: 'AeroData Dynamics Corp.',
    timezone: 'IST',
    ocrEngine: 'aws-textract',
    llmModel: 'gemini-1.5-flash',
    promptTemplate: '',
    syncAuto: true,
    syncValidation: true,
    webhookUrl: 'https://api.aerodata.io/v1/webhooks/excel-sync',
    apiKey: 'your_api_key_here'
  }
};

let appState = JSON.parse(localStorage.getItem('aerodata_xls_state')) || JSON.parse(JSON.stringify(DEFAULT_STATE));

// Save state back to local storage helper
function saveState() {
  localStorage.setItem('aerodata_xls_state', JSON.stringify(appState));
}

// 2. BOOTSTRAP INIT & PAGE DETECT
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  lucide.createIcons();
  
  // Highlight active link in sidebar matching current filename
  let filename = window.location.pathname.split('/').pop() || 'index.html';
  if (filename === 'index.html') filename = 'dashboard.html'; // default fallback
  
  document.querySelectorAll('.sidebar-nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === filename) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Mobile drawer sidebar toggle
  const mobileToggle = document.getElementById('mobile-toggle');
  const sidebar = document.getElementById('sidebar');
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('show');
    });
  }

  // Bind settings subtabs if they exist on settings page
  document.querySelectorAll('.settings-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('.settings-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      const targetSubtab = link.getAttribute('data-subtab');
      
      document.querySelectorAll('.settings-panel').forEach(p => {
        p.classList.add('d-none');
        p.classList.remove('active');
      });
      const targetPanel = document.getElementById(`settings-panel-${targetSubtab}`);
      if (targetPanel) {
        targetPanel.classList.remove('d-none');
        targetPanel.classList.add('active');
      }
    });
  });

  // Universal initializers
  updateKPIs();
  initThemeToggle();
  initGlobalSearch();
  initNotifications();
  checkActiveJobs(); // Handles background parsing simulations on any page load!

  // Page Specific initializations based on DOM presence
  if (document.getElementById('dashboard-recent-uploads-tbody')) {
    initDashboard();
  }
  if (document.getElementById('drag-drop-zone')) {
    initUploads();
  }
  if (document.getElementById('queue-cards-container')) {
    initQueue();
  }
  if (document.getElementById('records-search')) {
    initRecordsTable();
  }
  if (document.getElementById('excel-filename-display')) {
    initExcelManagement();
  }
  if (document.getElementById('reports-avg-time')) {
    initReports();
  }
  if (document.getElementById('logs-search')) {
    initLogs();
  }
  if (document.getElementById('users-tbody')) {
    initUsers();
  }
  if (document.getElementById('settings-save-btn')) {
    initSettings();
  }
});

// 3. THEME MANAGEMENT
function initTheme() {
  const currentTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon(currentTheme);
}

function initThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const activeTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      updateThemeIcon(newTheme);
      
      // Redraw charts if on dashboard or reports
      if (document.getElementById('dashboard-activity-chart')) renderDashboardCharts();
      if (document.getElementById('reports-monthly-bar-chart')) renderReportsCharts();
    });
  }
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    if (theme === 'dark') {
      icon.setAttribute('data-lucide', 'sun');
    } else {
      icon.setAttribute('data-lucide', 'moon');
    }
    lucide.createIcons();
  }
}

// 4. MOCK SYSTEM LOGS & NOTIFICATIONS
function addAuditLog(module, action, details, status = 'Success') {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 16);
  appState.logs.unshift({ timestamp, user: 'Sarah Connor', module, action, status, details });
  saveState();
  
  // Refresh logs table if on logs page
  if (document.getElementById('logs-tbody')) {
    initLogs();
  }
}

function addNotification(text, type = 'success') {
  const id = Date.now();
  appState.notifications.unshift({ id, text, time: 'Just Now', type });
  saveState();
  initNotifications();
}

function initNotifications() {
  const badge = document.getElementById('notif-badge');
  const list = document.getElementById('notif-items-container');
  const clearBtn = document.getElementById('clear-notifs-btn');
  
  if (appState.notifications.length > 0) {
    if (badge) badge.classList.remove('d-none');
  } else {
    if (badge) badge.classList.add('d-none');
  }

  if (list) {
    if (appState.notifications.length === 0) {
      list.innerHTML = `<li class="px-3 py-3 border-bottom border-color text-center text-muted" style="font-size: 0.85rem;">No new notifications</li>`;
    } else {
      list.innerHTML = appState.notifications.map(n => `
        <li class="px-3 py-2 border-bottom border-color d-flex align-items-start gap-2">
          <div class="mt-1">
            ${n.type === 'error' ? '<i data-lucide="x-circle" class="text-danger" style="width:16px;"></i>' : '<i data-lucide="check-circle" class="text-success" style="width:16px;"></i>'}
          </div>
          <div style="font-size: 0.85rem; flex: 1;">
            <div class="text-main">${n.text}</div>
            <div class="text-muted" style="font-size:0.75rem;">${n.time}</div>
          </div>
        </li>
      `).join('');
      lucide.createIcons();
    }
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', (e) => {
      e.preventDefault();
      appState.notifications = [];
      saveState();
      initNotifications();
    });
  }
}

// 5. GLOBAL SEARCH BAR
function initGlobalSearch() {
  const searchInput = document.getElementById('global-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) return;

      // If on records page, filter table
      if (document.getElementById('records-search')) {
        document.getElementById('records-search').value = q;
        document.getElementById('records-search').dispatchEvent(new Event('input'));
      }
      
      // If on uploads page, filter table
      if (document.getElementById('pdf-registry-tbody')) {
        const trs = document.querySelectorAll('#pdf-registry-tbody tr');
        trs.forEach(tr => {
          const txt = tr.innerText.toLowerCase();
          tr.style.display = txt.includes(q) ? '' : 'none';
        });
      }
    });
  }
}

// 6. DASHBOARD PAGE INITIALIZATION
function initDashboard() {
  updateKPIs();
  
  // Recent Uploads mini-table
  const recentUploadsBody = document.getElementById('dashboard-recent-uploads-tbody');
  if (recentUploadsBody) {
    const recents = appState.files.slice(0, 4);
    recentUploadsBody.innerHTML = recents.map(f => `
      <tr>
        <td class="fw-semibold">${f.name}</td>
        <td><span class="badge-custom badge-primary-custom">${f.category}</span></td>
        <td>${f.date}</td>
        <td>
          <span class="badge-custom ${f.status === 'Completed' ? 'badge-success-custom' : f.status === 'Failed' ? 'badge-error-custom' : 'badge-warning-custom'}">
            ${f.status}
          </span>
        </td>
        <td class="fw-semibold">${f.recordsCount}</td>
      </tr>
    `).join('');
  }

  // Recent Activities feed
  const recentActivitiesContainer = document.getElementById('dashboard-recent-activities-container');
  if (recentActivitiesContainer) {
    const recentLogs = appState.logs.slice(0, 4);
    recentActivitiesContainer.innerHTML = recentLogs.map(l => {
      let icon = 'info';
      let iconColor = 'text-primary';
      if (l.status === 'Error') { icon = 'alert-triangle'; iconColor = 'text-danger'; }
      else if (l.action.includes('Upload')) { icon = 'file-up'; iconColor = 'text-info'; }
      else if (l.action.includes('Excel')) { icon = 'file-spreadsheet'; iconColor = 'text-success'; }

      return `
        <div class="d-flex align-items-start gap-3">
          <div class="p-2 border border-color rounded-circle bg-light d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
            <i data-lucide="${icon}" class="${iconColor}" style="width: 16px; height: 16px;"></i>
          </div>
          <div style="flex: 1; font-size: 0.85rem;">
            <div class="d-flex justify-content-between">
              <span class="fw-semibold text-main">${l.action}</span>
              <span class="text-muted" style="font-size: 0.75rem;">${l.timestamp.split(' ')[1] || l.timestamp}</span>
            </div>
            <p class="text-muted mb-0">${l.details}</p>
          </div>
        </div>
      `;
    }).join('');
    lucide.createIcons();
  }
  
  // Weekly/monthly chart toggler
  const weekBtn = document.getElementById('chart-week-btn');
  const monthBtn = document.getElementById('chart-month-btn');
  if (weekBtn && monthBtn) {
    weekBtn.addEventListener('click', () => {
      weekBtn.classList.add('active');
      monthBtn.classList.remove('active');
      renderDashboardCharts('week');
    });
    monthBtn.addEventListener('click', () => {
      monthBtn.classList.add('active');
      weekBtn.classList.remove('active');
      renderDashboardCharts('month');
    });
  }

  // Draw charts
  renderDashboardCharts();
}

function updateKPIs() {
  const countTotal = appState.files.length;
  const countProcessed = appState.files.filter(f => f.status === 'Completed').length;
  const countPending = appState.files.filter(f => f.status === 'Pending' || f.status === 'Processing').length;
  const countFailed = appState.files.filter(f => f.status === 'Failed').length;
  const totalRecords = appState.records.length;

  const totalUploadsEl = document.getElementById('kpi-total-uploads');
  const processedEl = document.getElementById('kpi-processed');
  const pendingEl = document.getElementById('kpi-pending');
  const failedEl = document.getElementById('kpi-failed');
  const recordsEl = document.getElementById('kpi-records');
  const rowsEl = document.getElementById('kpi-excel-rows');

  if (totalUploadsEl) totalUploadsEl.textContent = countTotal;
  if (processedEl) processedEl.textContent = countProcessed;
  if (pendingEl) pendingEl.textContent = countPending;
  if (failedEl) failedEl.textContent = countFailed;
  if (recordsEl) recordsEl.textContent = totalRecords;
  if (rowsEl) rowsEl.textContent = totalRecords;
  
  // Update status dot in top header (exists on all pages)
  const indicator = document.getElementById('processing-status-indicator');
  if (indicator) {
    const dot = indicator.querySelector('.status-dot');
    const txt = indicator.querySelector('.status-text');
    if (countPending > 0) {
      dot.className = 'status-dot processing';
      txt.textContent = `${countPending} File(s) Processing`;
    } else {
      dot.className = 'status-dot';
      txt.textContent = 'System Idle';
    }
  }
}

// 7. PDF UPLOADS PAGE
function initUploads() {
  const dropZone = document.getElementById('drag-drop-zone');
  const fileInput = document.getElementById('file-input-selector');
  const uploadForm = document.getElementById('pdf-upload-form');

  if (dropZone && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      handleSelectedFiles(files);
    });

    fileInput.addEventListener('change', (e) => {
      handleSelectedFiles(e.target.files);
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const filesToUpload = fileInput.files;
      if (filesToUpload.length === 0 && selectedFilesList.length === 0) {
        alert('Please choose or drag at least one PDF document to import.');
        return;
      }

      const overrideBatchName = document.getElementById('upload-doc-name').value;
      const category = document.getElementById('upload-category').value || 'Invoice';
      const notes = document.getElementById('upload-notes').value;
      const tags = document.getElementById('upload-tags').value;

      triggerMockUploads(overrideBatchName, category, tags, notes);
    });
  }

  renderPDFRegistry();

  // Category filter trigger
  const categoryFilter = document.getElementById('table-filter-category');
  if (categoryFilter) {
    categoryFilter.addEventListener('change', (e) => {
      renderPDFRegistry(e.target.value);
    });
  }
}

let selectedFilesList = [];
function handleSelectedFiles(files) {
  selectedFilesList = Array.from(files).filter(f => f.type === 'application/pdf');
  const batchNameInput = document.getElementById('upload-doc-name');
  if (batchNameInput && selectedFilesList.length > 0) {
    batchNameInput.value = selectedFilesList.length === 1 
      ? selectedFilesList[0].name.replace('.pdf', '') 
      : `Batch_${new Date().toISOString().substring(0,10)}_PDFs`;
  }
  addAuditLog('Upload', 'Files Inspected', `Loaded ${selectedFilesList.length} files in drag-drop zone.`);
}

function triggerMockUploads(batchName, category, tags, notes) {
  if (selectedFilesList.length === 0) {
    selectedFilesList = [{ name: batchName ? `${batchName}.pdf` : 'invoice_imported_batch.pdf', size: 1024 * 1280 }];
  }

  const container = document.getElementById('active-uploads-progress-container');
  const card = document.getElementById('active-uploads-progress-card');
  
  if (container && card) {
    card.classList.remove('d-none');
  }

  selectedFilesList.forEach((file, index) => {
    const fileId = `F-${Date.now().toString().slice(-3)}-${index}`;
    const sizeStr = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
    
    // Inject file in state directly as Processing to start workflow
    const newFile = {
      id: fileId,
      name: file.name,
      category: category,
      date: new Date().toISOString().replace('T', ' ').substring(0, 16),
      status: 'Processing', // Immediately starts workflow!
      processingStartTime: Date.now(), // Sets the clock ticking!
      recordsCount: 0,
      size: sizeStr,
      duration: '0s'
    };
    appState.files.unshift(newFile);
    saveState();
    
    addAuditLog('Upload', 'Upload Finished', `Successfully uploaded ${file.name}.`, 'Success');
    addNotification(`File uploaded: ${file.name}`);
  });

  // Redirect user to processing queue immediately so they can watch the live monitor!
  window.location.href = 'processing-queue.html';
}

function renderPDFRegistry(filterCat = 'All') {
  const body = document.getElementById('pdf-registry-tbody');
  if (!body) return;

  const filtered = filterCat === 'All' 
    ? appState.files 
    : appState.files.filter(f => f.category === filterCat);

  if (filtered.length === 0) {
    body.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No PDF documents registered.</td></tr>`;
    return;
  }

  body.innerHTML = filtered.map(f => `
    <tr>
      <td class="fw-semibold text-break">${f.name}</td>
      <td><span class="badge-custom badge-primary-custom">${f.category}</span></td>
      <td class="text-muted" style="font-size:0.8rem;">${f.date}</td>
      <td>
        <span class="badge-custom ${f.status === 'Completed' ? 'badge-success-custom' : f.status === 'Failed' ? 'badge-error-custom' : 'badge-warning-custom'}">
          ${f.status}
        </span>
      </td>
      <td class="fw-semibold">${f.recordsCount}</td>
      <td class="text-muted">${f.duration}</td>
      <td>
        <div class="dropdown">
          <button class="btn btn-link btn-sm text-muted p-0" data-bs-toggle="dropdown">
            <i data-lucide="more-vertical" style="width:16px;"></i>
          </button>
          <ul class="dropdown-menu dropdown-menu-end modal-content-custom">
            <li><a class="dropdown-item py-2" href="#" onclick="processFileDirectly('${f.id}')"><i data-lucide="play" class="me-2" style="width:14px;"></i> Process</a></li>
            <li><a class="dropdown-item py-2" href="#" onclick="reprocessFileDirectly('${f.id}')"><i data-lucide="refresh-cw" class="me-2" style="width:14px;"></i> Reprocess</a></li>
            <li><a class="dropdown-item py-2 text-danger" href="#" onclick="deleteFileDirectly('${f.id}')"><i data-lucide="trash-2" class="me-2" style="width:14px;"></i> Delete</a></li>
          </ul>
        </div>
      </td>
    </tr>
  `).join('');
  lucide.createIcons();
}

window.processFileDirectly = function(fileId) {
  const file = appState.files.find(f => f.id === fileId);
  if (file && file.status !== 'Processing') {
    file.status = 'Processing';
    file.processingStartTime = Date.now();
    saveState();
    window.location.href = 'processing-queue.html';
  }
};

window.reprocessFileDirectly = function(fileId) {
  appState.records = appState.records.filter(r => r.fileId !== fileId);
  const file = appState.files.find(f => f.id === fileId);
  if (file) {
    file.status = 'Processing';
    file.recordsCount = 0;
    file.processingStartTime = Date.now();
    saveState();
    window.location.href = 'processing-queue.html';
  }
};

window.deleteFileDirectly = function(fileId) {
  const file = appState.files.find(f => f.id === fileId);
  if (confirm(`Remove file ${file ? file.name : fileId} and delete its records?`)) {
    appState.files = appState.files.filter(f => f.id !== fileId);
    appState.records = appState.records.filter(r => r.fileId !== fileId);
    saveState();
    
    addAuditLog('Upload', 'File Deleted', `Deleted PDF registry ID: ${fileId}.`);
    renderPDFRegistry();
    updateKPIs();
  }
};

// 8. COHESIVE BACKGROUND JOBS RUNNER (MPA PERSISTENCE)
function checkActiveJobs() {
  let stateChanged = false;
  appState.files.forEach(file => {
    if (file.status === 'Processing') {
      const startTime = file.processingStartTime || Date.now();
      const elapsed = Date.now() - startTime;
      const durationMs = 3000; // 3 seconds mock duration
      
      if (elapsed >= durationMs) {
        completeFileJob(file);
        stateChanged = true;
      } else {
        resumeActiveJobSimulation(file, elapsed, durationMs);
      }
    }
  });
  if (stateChanged) {
    saveState();
    updateKPIs();
  }
}

function completeFileJob(file) {
  file.status = 'Completed';
  file.duration = ((Math.random() * 1.5) + 0.8).toFixed(1) + 's';
  
  // Generate mock records
  let generatedRecords = [];
  const invoiceNumber = 'INV-' + Math.floor(100000 + Math.random() * 900000);
  const randomAmount = (Math.random() * 2500 + 40).toFixed(2);
  const taxAmount = (randomAmount * 0.08).toFixed(2);
  
  if (file.category === 'Invoice' || file.category === 'Receipt') {
    generatedRecords.push({
      id: `REC-${Math.floor(100 + Math.random() * 900)}`,
      fileId: file.id,
      fileName: file.name,
      invoiceNum: invoiceNumber,
      customer: file.category === 'Invoice' ? 'TechVanguard Systems' : 'Starbucks Corp #4412',
      date: new Date().toISOString().substring(0, 10),
      amount: parseFloat(randomAmount),
      tax: parseFloat(taxAmount),
      status: 'Valid'
    });
  } else if (file.category === 'Bank Statement') {
    for (let i = 1; i <= 3; i++) {
      const amt = (Math.random() * 800 - 300).toFixed(2);
      generatedRecords.push({
        id: `REC-${Math.floor(100 + Math.random() * 900)}`,
        fileId: file.id,
        fileName: file.name,
        invoiceNum: `TXN-${invoiceNumber}-${i}`,
        customer: amt > 0 ? 'Direct Deposit ACH' : 'AWS Cloud Bill Services',
        date: new Date().toISOString().substring(0, 10),
        amount: parseFloat(amt),
        tax: 0.00,
        status: parseFloat(amt) === 0 ? 'Review' : 'Valid'
      });
    }
  } else {
    generatedRecords.push({
      id: `REC-${Math.floor(100 + Math.random() * 900)}`,
      fileId: file.id,
      fileName: file.name,
      invoiceNum: `REF-${invoiceNumber}`,
      customer: 'Global Logistics Alliance',
      date: new Date().toISOString().substring(0, 10),
      amount: 4500.00,
      tax: 360.00,
      status: 'Review'
    });
  }

  file.recordsCount = generatedRecords.length;
  appState.records.push(...generatedRecords);
  
  // Append log and notification
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 16);
  appState.logs.unshift({
    timestamp,
    user: 'Sarah Connor',
    module: 'Parser',
    action: 'Extraction Succeeded',
    status: 'Success',
    details: `Extracted ${generatedRecords.length} records from ${file.name} (Background compilation).`
  });
  appState.notifications.unshift({
    id: Date.now() + Math.random(),
    text: `${generatedRecords.length} records parsed from ${file.name}`,
    time: 'Just Now',
    type: 'success'
  });
}

function resumeActiveJobSimulation(file, elapsed, durationMs) {
  const fileId = file.id;
  
  // Detect step based on elapsed time (1s per step)
  let step = 1;
  if (elapsed > 1000) step = 2;
  if (elapsed > 2000) step = 3;
  
  const interval = setInterval(() => {
    elapsed += 500;
    
    if (elapsed >= durationMs) {
      clearInterval(interval);
      let freshFile = appState.files.find(f => f.id === fileId);
      if (freshFile && freshFile.status === 'Processing') {
        completeFileJob(freshFile);
        saveState();
        
        // Redraw current page elements
        updateKPIs();
        if (document.getElementById('queue-cards-container')) initQueue();
        if (document.getElementById('records-search')) renderRecords();
        if (document.getElementById('excel-filename-display')) initExcelManagement();
        if (document.getElementById('dashboard-recent-uploads-tbody')) initDashboard();
      }
      return;
    }
    
    // Animate progress on queue UI if user is looking at it
    const newStep = elapsed > 2000 ? 3 : elapsed > 1000 ? 2 : 1;
    if (newStep !== step) {
      step = newStep;
      const stepEl = document.querySelector(`#job-${fileId}-step-${step}`);
      const prevStepEl = document.querySelector(`#job-${fileId}-step-${step - 1}`);
      const progressEl = document.querySelector(`#job-${fileId}-progress`);

      if (prevStepEl) {
        prevStepEl.classList.remove('active');
        prevStepEl.classList.add('completed');
      }
      if (stepEl) stepEl.classList.add('active');
      if (progressEl) progressEl.style.width = (step === 2 ? '66%' : '100%');
    }
  }, 500);
}

// 9. PROCESSING QUEUE VIEW
function initQueue() {
  const container = document.getElementById('queue-cards-container');
  const banner = document.getElementById('queue-active-banner');
  const bulkBtn = document.getElementById('bulk-process-btn');
  
  if (!container) return;

  const countPending = appState.files.filter(f => f.status === 'Pending').length;
  const countRunning = appState.files.filter(f => f.status === 'Processing').length;
  const countCompleted = appState.files.filter(f => f.status === 'Completed').length;
  const countFailed = appState.files.filter(f => f.status === 'Failed').length;

  document.getElementById('queue-stat-pending').textContent = countPending;
  document.getElementById('queue-stat-running').textContent = countRunning;
  document.getElementById('queue-stat-completed').textContent = countCompleted;
  document.getElementById('queue-stat-failed').textContent = countFailed;

  if (banner) banner.textContent = `${countRunning} Active Jobs`;

  const queueFiles = appState.files.filter(f => f.status === 'Pending' || f.status === 'Processing');

  if (queueFiles.length === 0) {
    container.innerHTML = `
      <div class="col-12 text-center text-muted py-5">
        <i data-lucide="check-circle" class="text-success mb-3" style="width:48px; height:48px;"></i>
        <h4>No Active Jobs in Queue</h4>
        <p class="mb-0">All files have been successfully processed or are awaiting uploads.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = queueFiles.map(f => {
    const isRunning = f.status === 'Processing';
    
    // Determine initial state based on elapsed time since the job started
    let stepPercent = '0%';
    let step1Class = '';
    let step2Class = '';
    let step3Class = '';
    
    if (isRunning && f.processingStartTime) {
      const elapsed = Date.now() - f.processingStartTime;
      if (elapsed > 2000) {
        stepPercent = '100%';
        step1Class = 'completed';
        step2Class = 'completed';
        step3Class = 'active';
      } else if (elapsed > 1000) {
        stepPercent = '66%';
        step1Class = 'completed';
        step2Class = 'active';
      } else {
        stepPercent = '33%';
        step1Class = 'active';
      }
    }

    return `
      <div class="col-12 col-md-6">
        <div class="card-custom queue-card ${isRunning ? 'running' : 'pending'} h-100 mb-0">
          <div class="d-flex justify-content-between mb-3">
            <div>
              <h4 class="h6 fw-bold mb-1 text-break">${f.name}</h4>
              <span class="text-muted" style="font-size:0.75rem;">Size: ${f.size} | Batch Category: ${f.category}</span>
            </div>
            <span class="badge-custom ${isRunning ? 'badge-warning-custom' : 'badge-primary-custom'}">
              ${f.status}
            </span>
          </div>

          <div class="progress mb-3" style="height: 6px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated ${isRunning ? 'bg-warning' : 'bg-primary'}" role="progressbar" style="width: ${stepPercent}" id="job-${f.id}-progress"></div>
          </div>

          <!-- Step tracker -->
          <div class="step-tracker">
            <div class="step-item ${step1Class}" id="job-${f.id}-step-1">
              <div class="step-dot">1</div>
              <span>OCR Parse</span>
            </div>
            <div class="step-item ${step2Class}" id="job-${f.id}-step-2">
              <div class="step-dot">2</div>
              <span>AI Fields</span>
            </div>
            <div class="step-item ${step3Class}" id="job-${f.id}-step-3">
              <div class="step-dot">3</div>
              <span>XLS Sync</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
  lucide.createIcons();

  if (bulkBtn) {
    bulkBtn.onclick = () => {
      const pendings = appState.files.filter(f => f.status === 'Pending');
      if (pendings.length === 0) {
        alert('No pending files to process.');
        return;
      }
      pendings.forEach(f => {
        f.status = 'Processing';
        f.processingStartTime = Date.now();
      });
      saveState();
      checkActiveJobs();
      initQueue();
    };
  }
}

// 10. EXTRACTED RECORDS PAGE
let recordsPageSize = 5;
let recordsCurrentPage = 1;
let recordsSortField = 'id';
let recordsSortOrder = 'desc';

function initRecordsTable() {
  const searchInput = document.getElementById('records-search');
  const sourceFilter = document.getElementById('records-filter-pdf');
  const minAmtInput = document.getElementById('records-filter-min-amt');
  const maxAmtInput = document.getElementById('records-filter-max-amt');
  const statusFilter = document.getElementById('records-filter-status');
  const resetBtn = document.getElementById('reset-records-filters');
  const dlCsvBtn = document.getElementById('records-download-csv-btn');
  const bulkDelBtn = document.getElementById('bulk-delete-records-btn');
  
  if (!searchInput) return;

  // Build PDF Filter options
  const uniquePDFs = [...new Set(appState.records.map(r => r.fileName))];
  sourceFilter.innerHTML = `<option value="All">All Documents</option>` + uniquePDFs.map(name => `<option value="${name}">${name}</option>`).join('');

  // Event Listeners for Filters
  [searchInput, minAmtInput, maxAmtInput].forEach(el => {
    el.addEventListener('input', () => { recordsCurrentPage = 1; renderRecords(); });
  });
  
  [sourceFilter, statusFilter].forEach(el => {
    el.addEventListener('change', () => { recordsCurrentPage = 1; renderRecords(); });
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      searchInput.value = '';
      sourceFilter.value = 'All';
      minAmtInput.value = '';
      maxAmtInput.value = '';
      statusFilter.value = 'All';
      recordsCurrentPage = 1;
      renderRecords();
    });
  }

  // Column sorting binding
  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const field = th.getAttribute('data-sort');
      if (recordsSortField === field) {
        recordsSortOrder = recordsSortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        recordsSortField = field;
        recordsSortOrder = 'asc';
      }
      renderRecords();
    });
  });

  // Select all checkbox
  const selectAllChk = document.getElementById('select-all-records-checkbox');
  if (selectAllChk) {
    selectAllChk.addEventListener('change', (e) => {
      const chks = document.querySelectorAll('.record-row-checkbox');
      chks.forEach(c => c.checked = e.target.checked);
    });
  }

  if (dlCsvBtn) {
    dlCsvBtn.addEventListener('click', () => downloadFilteredCSV());
  }

  if (bulkDelBtn) {
    bulkDelBtn.addEventListener('click', () => {
      const selectedChks = document.querySelectorAll('.record-row-checkbox:checked');
      if (selectedChks.length === 0) {
        alert('Please check at least one record to delete.');
        return;
      }
      if (confirm(`Delete ${selectedChks.length} selected records?`)) {
        const idsToDelete = Array.from(selectedChks).map(c => c.getAttribute('data-rec-id'));
        appState.records = appState.records.filter(r => !idsToDelete.includes(r.id));
        saveState();
        addAuditLog('Excel', 'Bulk Delete', `Deleted ${idsToDelete.length} records.`);
        
        recordsCurrentPage = 1;
        renderRecords();
        updateKPIs();
      }
    });
  }

  // Drawer events
  const closeDrawerBtn = document.getElementById('close-drawer-btn');
  const backdrop = document.getElementById('record-drawer-backdrop');
  if (closeDrawerBtn && backdrop) {
    [closeDrawerBtn, backdrop].forEach(el => {
      el.addEventListener('click', closeRecordDrawer);
    });
  }

  // Edit record form
  const editForm = document.getElementById('edit-record-form');
  if (editForm) {
    editForm.addEventListener('submit', handleEditRecordSubmit);
  }

  renderRecords();
}

function renderRecords() {
  const searchVal = document.getElementById('records-search').value.toLowerCase().trim();
  const sourceVal = document.getElementById('records-filter-pdf').value;
  const minAmt = parseFloat(document.getElementById('records-filter-min-amt').value) || -999999;
  const maxAmt = parseFloat(document.getElementById('records-filter-max-amt').value) || 999999;
  const statusVal = document.getElementById('records-filter-status').value;

  let filtered = appState.records.filter(r => {
    const textMatch = r.customer.toLowerCase().includes(searchVal) || r.invoiceNum.toLowerCase().includes(searchVal) || r.id.toLowerCase().includes(searchVal);
    const sourceMatch = sourceVal === 'All' || r.fileName === sourceVal;
    const amountMatch = r.amount >= minAmt && r.amount <= maxAmt;
    const statusMatch = statusVal === 'All' || r.status === statusVal;

    return textMatch && sourceMatch && amountMatch && statusMatch;
  });

  filtered.sort((a, b) => {
    let valA = a[recordsSortField];
    let valB = b[recordsSortField];

    if (typeof valA === 'string') {
      valA = valA.toLowerCase();
      valB = valB.toLowerCase();
    }

    if (valA < valB) return recordsSortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return recordsSortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const totalRecords = filtered.length;
  const totalPages = Math.ceil(totalRecords / recordsPageSize);
  
  if (recordsCurrentPage > totalPages && totalPages > 0) {
    recordsCurrentPage = totalPages;
  }

  const startIndex = (recordsCurrentPage - 1) * recordsPageSize;
  const endIndex = Math.min(startIndex + recordsPageSize, totalRecords);
  const paginatedRecords = filtered.slice(startIndex, endIndex);

  const tbody = document.getElementById('records-tbody');
  if (tbody) {
    if (paginatedRecords.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No records found matching filters.</td></tr>`;
      document.getElementById('records-pagination-info').textContent = `Showing 0 to 0 of 0 records`;
      document.getElementById('records-pagination-list').innerHTML = '';
      return;
    }

    tbody.innerHTML = paginatedRecords.map(r => `
      <tr>
        <td><input type="checkbox" class="record-row-checkbox" data-rec-id="${r.id}"></td>
        <td class="fw-semibold text-primary" onclick="openRecordDrawer('${r.id}')" style="cursor:pointer;">${r.id}</td>
        <td class="text-truncate text-muted text-break" style="max-width: 140px;" title="${r.fileName}">${r.fileName}</td>
        <td>${r.invoiceNum}</td>
        <td class="fw-semibold">${r.customer}</td>
        <td>${r.date}</td>
        <td class="${r.amount < 0 ? 'text-danger fw-semibold' : 'fw-semibold'}">$${r.amount.toFixed(2)}</td>
        <td class="text-muted">$${r.tax.toFixed(2)}</td>
        <td>
          <span class="badge-custom ${r.status === 'Valid' ? 'badge-success-custom' : r.status === 'Review' ? 'badge-warning-custom' : 'badge-error-custom'}">
            ${r.status}
          </span>
        </td>
        <td>
          <div class="d-flex gap-2">
            <button class="btn btn-outline-primary btn-sm px-2" onclick="openEditRecordModal('${r.id}')" title="Edit row" data-bs-toggle="modal" data-bs-target="#editRecordModal">
              <i data-lucide="edit-2" style="width:14px; height:14px;"></i>
            </button>
            <button class="btn btn-outline-danger btn-sm px-2" onclick="deleteRecordDirectly('${r.id}')" title="Delete row">
              <i data-lucide="trash" style="width:14px; height:14px;"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
    lucide.createIcons();

    document.getElementById('records-pagination-info').textContent = `Showing ${startIndex + 1} to ${endIndex} of ${totalRecords} records`;
    renderPaginationButtons(totalPages);
  }
}

function renderPaginationButtons(totalPages) {
  const list = document.getElementById('records-pagination-list');
  if (!list) return;

  let btns = `
    <li class="page-item ${recordsCurrentPage === 1 ? 'disabled' : ''}">
      <a class="page-link" href="#" onclick="changeRecordsPage(${recordsCurrentPage - 1})"><i data-lucide="chevron-left" style="width:14px;"></i></a>
    </li>
  `;

  for (let i = 1; i <= totalPages; i++) {
    btns += `
      <li class="page-item ${recordsCurrentPage === i ? 'active' : ''}">
        <a class="page-link" href="#" onclick="changeRecordsPage(${i})">${i}</a>
      </li>
    `;
  }

  btns += `
    <li class="page-item ${recordsCurrentPage === totalPages ? 'disabled' : ''}">
      <a class="page-link" href="#" onclick="changeRecordsPage(${recordsCurrentPage + 1})"><i data-lucide="chevron-right" style="width:14px;"></i></a>
    </li>
  `;

  list.innerHTML = btns;
  lucide.createIcons();
}

window.changeRecordsPage = function(pageNumber) {
  recordsCurrentPage = pageNumber;
  renderRecords();
};

window.openRecordDrawer = function(recId) {
  const r = appState.records.find(item => item.id === recId);
  if (!r) return;

  const file = appState.files.find(f => f.id === r.fileId) || { category: 'Invoice', date: '2026-07-12 10:00' };

  document.getElementById('drawer-subtitle-id').textContent = `ID: ${r.id}`;
  document.getElementById('drawer-file-name').textContent = r.fileName;
  document.getElementById('drawer-file-category').innerHTML = `<span class="badge-custom badge-primary-custom">${file.category}</span>`;
  document.getElementById('drawer-file-date').textContent = file.date;

  const fieldsTbody = document.getElementById('drawer-fields-tbody');
  fieldsTbody.innerHTML = `
    <tr>
      <td class="fw-semibold">Invoice Number</td>
      <td><code>${r.invoiceNum}</code></td>
      <td><span class="text-success"><i data-lucide="check" style="width:14px;"></i> Confirmed</span></td>
    </tr>
    <tr>
      <td class="fw-semibold">Customer Profile</td>
      <td>${r.customer}</td>
      <td><span class="text-success"><i data-lucide="check" style="width:14px;"></i> Confirmed</span></td>
    </tr>
    <tr>
      <td class="fw-semibold">Subtotal Amount</td>
      <td class="fw-bold">$${r.amount.toFixed(2)}</td>
      <td><span class="text-success"><i data-lucide="check" style="width:14px;"></i> Confirmed</span></td>
    </tr>
    <tr>
      <td class="fw-semibold">Estimated Taxes</td>
      <td>$${r.tax.toFixed(2)}</td>
      <td><span class="text-success"><i data-lucide="check" style="width:14px;"></i> Confirmed</span></td>
    </tr>
    <tr>
      <td class="fw-semibold">Verification Total</td>
      <td class="fw-bold">$${(r.amount + r.tax).toFixed(2)}</td>
      <td><span class="${r.amount < 0 ? 'text-warning' : 'text-success'}">${r.amount < 0 ? '<i data-lucide="alert-circle" style="width:14px;"></i> Warning' : '<i data-lucide="check" style="width:14px;"></i> Validated'}</span></td>
    </tr>
  `;

  const checkContainer = document.getElementById('drawer-validation-container');
  const calculationsMatch = r.amount >= 0;
  
  checkContainer.innerHTML = `
    <div class="d-flex align-items-center justify-content-between p-2 rounded bg-light border border-color">
      <span><i data-lucide="check-circle-2" class="text-success me-2" style="width:16px;"></i> OCR Layout Structure Match</span>
      <span class="badge bg-success-subtle text-success">Pass</span>
    </div>
    <div class="d-flex align-items-center justify-content-between p-2 rounded bg-light border border-color">
      <span><i data-lucide="${calculationsMatch ? 'check-circle-2' : 'alert-circle'}" class="${calculationsMatch ? 'text-success' : 'text-warning'} me-2" style="width:16px;"></i> Sum Arithmetic Match</span>
      <span class="badge ${calculationsMatch ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'}">${calculationsMatch ? 'Pass' : 'Manual Review'}</span>
    </div>
    <div class="d-flex align-items-center justify-content-between p-2 rounded bg-light border border-color">
      <span><i data-lucide="check-circle-2" class="text-success me-2" style="width:16px;"></i> Schema Field Type Match</span>
      <span class="badge bg-success-subtle text-success">Pass</span>
    </div>
  `;

  const histContainer = document.getElementById('drawer-history-container');
  histContainer.innerHTML = `
    <div class="position-relative mb-2">
      <div class="position-absolute" style="left: -23px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background-color: var(--success-color);"></div>
      <div class="fw-bold">Dynamic Excel Sync Finished</div>
      <div class="text-muted" style="font-size:0.75rem;">Appended into master dataset successfully.</div>
    </div>
    <div class="position-relative mb-2">
      <div class="position-absolute" style="left: -23px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background-color: var(--success-color);"></div>
      <div class="fw-bold">LLM Field Verification Done</div>
      <div class="text-muted" style="font-size:0.75rem;">Prompt parameters matched with 99.1% parsing safety.</div>
    </div>
    <div class="position-relative">
      <div class="position-absolute" style="left: -23px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background-color: var(--success-color);"></div>
      <div class="fw-bold">OCR Text Scanner Completed</div>
      <div class="text-muted" style="font-size:0.75rem;">Extracted PDF character block arrays.</div>
    </div>
  `;

  lucide.createIcons();

  document.getElementById('record-drawer-backdrop').classList.add('show');
  document.getElementById('record-detail-drawer').classList.add('show');
};

function closeRecordDrawer() {
  document.getElementById('record-drawer-backdrop').classList.remove('show');
  document.getElementById('record-detail-drawer').classList.remove('show');
}

window.openEditRecordModal = function(recId) {
  const r = appState.records.find(item => item.id === recId);
  if (!r) return;

  document.getElementById('edit-record-idx').value = r.id;
  document.getElementById('edit-customer').value = r.customer;
  document.getElementById('edit-invoice-num').value = r.invoiceNum;
  document.getElementById('edit-date').value = r.date;
  document.getElementById('edit-amount').value = r.amount;
  document.getElementById('edit-tax').value = r.tax;
  document.getElementById('edit-status').value = r.status;
};

function handleEditRecordSubmit(e) {
  e.preventDefault();
  const recId = document.getElementById('edit-record-idx').value;
  const r = appState.records.find(item => item.id === recId);
  
  if (r) {
    r.customer = document.getElementById('edit-customer').value;
    r.invoiceNum = document.getElementById('edit-invoice-num').value;
    r.date = document.getElementById('edit-date').value;
    r.amount = parseFloat(document.getElementById('edit-amount').value) || 0;
    r.tax = parseFloat(document.getElementById('edit-tax').value) || 0;
    r.status = document.getElementById('edit-status').value;

    saveState();
    addAuditLog('Excel', 'Edit Fields', `Manually corrected invoice values on row: ${recId}.`);
    
    const modalEl = document.getElementById('editRecordModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    renderRecords();
    updateKPIs();
  }
}

// 11. EXCEL MANAGEMENT PAGE
function initExcelManagement() {
  const rowsCount = appState.records.length;
  document.getElementById('excel-stat-rows').textContent = rowsCount;
  document.getElementById('excel-stat-sources').textContent = `${appState.files.length} PDFs`;
  
  // Render Spreadsheet Preview
  const previewBody = document.getElementById('excel-preview-tbody');
  if (previewBody) {
    if (appState.records.length === 0) {
      previewBody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4">Workbook contains empty active sheets.</td></tr>`;
      return;
    }

    const previewRows = appState.records.slice(0, 12);
    previewBody.innerHTML = previewRows.map((r, i) => `
      <tr>
        <td class="text-center bg-light text-muted" style="background-color: var(--bg-app); font-weight:600;">${i + 1}</td>
        <td><code>${r.id}</code></td>
        <td class="text-muted">${r.fileName}</td>
        <td class="fw-semibold">${r.invoiceNum}</td>
        <td>${r.customer}</td>
        <td>${r.date}</td>
        <td class="fw-bold">${r.amount.toFixed(2)}</td>
        <td>${r.tax.toFixed(2)}</td>
        <td><span class="badge ${r.status === 'Valid' ? 'bg-success' : r.status === 'Review' ? 'bg-warning text-dark' : 'bg-danger'}">${r.status}</span></td>
      </tr>
    `).join('');
  }

  const newBtn = document.getElementById('excel-create-new-btn');
  if (newBtn) {
    newBtn.onclick = () => {
      if (confirm('Are you sure you want to initialize a fresh master Excel file? This deletes all currently generated rows!')) {
        appState.records = [];
        appState.files.forEach(f => {
          f.recordsCount = 0;
          if (f.status === 'Completed') f.status = 'Pending';
        });
        saveState();
        addAuditLog('Excel', 'Dataset Created', 'Initialized empty workbook master.');
        
        initExcelManagement();
        updateKPIs();
      }
    };
  }

  const masterDlBtn = document.getElementById('excel-master-download-btn');
  if (masterDlBtn) {
    masterDlBtn.onclick = () => downloadFilteredCSV(true);
  }
}

function downloadFilteredCSV(downloadAll = false) {
  let list = appState.records;

  if (list.length === 0) {
    alert('No rows selected or found to compile.');
    return;
  }

  const headers = ['Record ID', 'Source PDF', 'Invoice Number', 'Customer Name', 'Billing Date', 'Amount ($)', 'Tax ($)', 'Status'];
  const rows = list.map(r => [
    r.id,
    r.fileName,
    r.invoiceNum,
    `"${r.customer.replace(/"/g, '""')}"`,
    r.date,
    r.amount,
    r.tax,
    r.status
  ]);

  const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', downloadAll ? 'master_invoice_dataset_2026.csv' : 'extracted_invoices_filtered.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  addAuditLog('Excel', 'Excel Downloaded', `Generated export compilation for ${list.length} rows.`);
}

// 12. REPORTS PAGE
function initReports() {
  document.getElementById('reports-volume').textContent = appState.files.length * 4;
  renderReportsCharts();
}

function renderDashboardCharts(period = 'week') {
  const chartSvg = document.getElementById('dashboard-activity-chart');
  if (!chartSvg) return;

  const theme = document.documentElement.getAttribute('data-theme');
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#334155' : '#E2E8F0';
  const textLabelColor = isDark ? '#94A3B8' : '#64748B';

  const width = chartSvg.clientWidth || 600;
  const height = 240;
  chartSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  const data = period === 'week' 
    ? [2, 5, 8, 12, 10, 15, 14] 
    : [15, 22, 38, 45, 60, 52, 70, 85, 94, 82, 110, 122];

  const labels = period === 'week'
    ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const maxVal = Math.max(...data) + 2;
  const paddingX = 40;
  const paddingY = 30;

  let gridHTML = `
    <defs>
      <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#2563EB" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#2563EB" stop-opacity="0.0"/>
      </linearGradient>
    </defs>
  `;

  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const y = paddingY + ((height - 2 * paddingY) / ticks) * i;
    const val = Math.round(maxVal - (maxVal / ticks) * i);
    gridHTML += `
      <line class="chart-grid-line" x1="${paddingX}" y1="${y}" x2="${width - paddingX}" y2="${y}" stroke="${gridColor}" stroke-dasharray="3 3" />
      <text x="${paddingX - 10}" y="${y + 4}" fill="${textLabelColor}" font-size="10" text-anchor="end">${val}</text>
    `;
  }

  const stepX = (width - 2 * paddingX) / (data.length - 1);
  const coords = data.map((val, i) => {
    const x = paddingX + i * stepX;
    const y = height - paddingY - (val / maxVal) * (height - 2 * paddingY);
    return { x, y, val, label: labels[i] };
  });

  let linePath = `M ${coords[0].x} ${coords[0].y}`;
  let areaPath = `M ${coords[0].x} ${coords[0].y}`;
  
  for (let i = 1; i < coords.length; i++) {
    linePath += ` L ${coords[i].x} ${coords[i].y}`;
    areaPath += ` L ${coords[i].x} ${coords[i].y}`;
  }
  areaPath += ` L ${coords[coords.length - 1].x} ${height - paddingY} L ${coords[0].x} ${height - paddingY} Z`;

  gridHTML += `<path d="${areaPath}" fill="url(#area-gradient)" />`;
  gridHTML += `<path d="${linePath}" class="chart-line" stroke="#2563EB" stroke-width="3" fill="none" />`;

  coords.forEach(p => {
    gridHTML += `
      <circle class="chart-point" cx="${p.x}" cy="${p.y}" r="5" fill="#2563EB" stroke="${isDark ? '#1E293B' : '#FFFFFF'}" stroke-width="2" />
      <text x="${p.x}" y="${height - paddingY + 18}" fill="${textLabelColor}" font-size="10" text-anchor="middle">${p.label}</text>
      <title>${p.label}: ${p.val} PDFs</title>
    `;
  });

  chartSvg.innerHTML = gridHTML;

  renderSuccessDonut();
}

function renderSuccessDonut() {
  const donutSvg = document.getElementById('success-rate-donut');
  if (!donutSvg) return;

  const theme = document.documentElement.getAttribute('data-theme');
  const isDark = theme === 'dark';

  const processed = appState.files.filter(f => f.status === 'Completed').length;
  const failed = appState.files.filter(f => f.status === 'Failed').length;
  const total = processed + failed || 1;
  const successPct = ((processed / total) * 100).toFixed(1);

  const pctDisplay = document.getElementById('success-rate-pct');
  if (pctDisplay) pctDisplay.textContent = successPct + '%';

  const circumference = 2 * Math.PI * 35;
  const strokeOffset = circumference - (processed / total) * circumference;

  donutSvg.innerHTML = `
    <circle cx="50" cy="50" r="35" fill="none" stroke="${isDark ? '#334155' : '#E2E8F0'}" stroke-width="8" />
    <circle cx="50" cy="50" r="35" fill="none" stroke="#22C55E" stroke-width="8" 
      stroke-dasharray="${circumference}" 
      stroke-dashoffset="${strokeOffset}" 
      transform="rotate(-90 50 50)" 
      stroke-linecap="round" />
  `;
}

function renderReportsCharts() {
  renderSuccessDonut();

  const barSvg = document.getElementById('reports-monthly-bar-chart');
  if (!barSvg) return;

  const theme = document.documentElement.getAttribute('data-theme');
  const isDark = theme === 'dark';
  const gridColor = isDark ? '#334155' : '#E2E8F0';
  const textLabelColor = isDark ? '#94A3B8' : '#64748B';

  const width = barSvg.clientWidth || 500;
  const height = 240;
  barSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  const barData = [12, 18, 25, 42, 64, 52];
  const barLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  
  const maxVal = Math.max(...barData) + 10;
  const paddingX = 40;
  const paddingY = 30;

  let barHTML = '';
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const y = paddingY + ((height - 2 * paddingY) / ticks) * i;
    const val = Math.round(maxVal - (maxVal / ticks) * i);
    barHTML += `
      <line class="chart-grid-line" x1="${paddingX}" y1="${y}" x2="${width - paddingX}" y2="${y}" stroke="${gridColor}" />
      <text x="${paddingX - 10}" y="${y + 4}" fill="${textLabelColor}" font-size="10" text-anchor="end">${val}</text>
    `;
  }

  const numBars = barData.length;
  const chartWidth = width - 2 * paddingX;
  const barGap = 15;
  const totalGapsWidth = barGap * (numBars - 1);
  const barWidth = (chartWidth - totalGapsWidth) / numBars;

  barData.forEach((val, i) => {
    const x = paddingX + i * (barWidth + barGap);
    const barHeight = (val / maxVal) * (height - 2 * paddingY);
    const y = height - paddingY - barHeight;

    barHTML += `
      <rect class="chart-bar" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="#2563EB" />
      <text x="${x + barWidth / 2}" y="${height - paddingY + 16}" fill="${textLabelColor}" font-size="10" text-anchor="middle">${barLabels[i]}</text>
      <title>${barLabels[i]}: ${val} scans</title>
    `;
  });

  barSvg.innerHTML = barHTML;

  renderCategoryDonut();
  renderHeatmap();
  renderTopDocs();
}

function renderCategoryDonut() {
  const svg = document.getElementById('reports-category-donut');
  const legend = document.getElementById('reports-category-legend');
  if (!svg || !legend) return;

  const theme = document.documentElement.getAttribute('data-theme');
  const isDark = theme === 'dark';

  const categories = [
    { name: 'Invoices', count: 18, color: '#2563EB' },
    { name: 'Receipts', count: 14, color: '#10B981' },
    { name: 'Bank Stmts', count: 8, color: '#F59E0B' },
    { name: 'Contracts', count: 4, color: '#EF4444' }
  ];

  const total = categories.reduce((sum, c) => sum + c.count, 0);

  let accumulatedPercent = 0;
  let donutHTML = `<circle cx="50" cy="50" r="35" fill="none" stroke="${isDark ? '#1E293B' : '#F8FAFC'}" stroke-width="12" />`;
  const circumference = 2 * Math.PI * 35;

  categories.forEach(cat => {
    const percent = cat.count / total;
    const strokeDash = percent * circumference;
    const strokeOffset = circumference - strokeDash;
    const angleRotation = (accumulatedPercent * 360) - 90;

    donutHTML += `
      <circle cx="50" cy="50" r="35" fill="none" stroke="${cat.color}" stroke-width="10" 
        stroke-dasharray="${circumference}" 
        stroke-dashoffset="${strokeOffset}" 
        transform="rotate(${angleRotation} 50 50)" 
        stroke-linecap="butt" />
    `;
    accumulatedPercent += percent;
  });

  svg.innerHTML = donutHTML;

  legend.innerHTML = categories.map(c => {
    const pct = ((c.count / total) * 100).toFixed(0);
    return `
      <div class="d-flex align-items-center justify-content-between">
        <div class="d-flex align-items-center gap-2">
          <span style="display:inline-block; width:12px; height:12px; border-radius:3px; background-color:${c.color};"></span>
          <span style="font-size:0.85rem;" class="fw-semibold">${c.name}</span>
        </div>
        <span class="fw-bold" style="font-size:0.85rem;">${pct}% (${c.count})</span>
      </div>
    `;
  }).join('');
}

function renderHeatmap() {
  const container = document.getElementById('analytics-heatmap');
  if (!container) return;

  let cellsHTML = '';
  for (let i = 0; i < 42; i++) {
    const intensity = Math.floor(Math.random() * 6);
    cellsHTML += `<div class="heatmap-cell" data-intensity="${intensity}" title="Activity level: ${intensity}/5"></div>`;
  }
  container.innerHTML = cellsHTML;
}

function renderTopDocs() {
  const tbody = document.getElementById('reports-top-docs-tbody');
  if (!tbody) return;

  const sorted = [...appState.files].sort((a,b) => b.recordsCount - a.recordsCount).slice(0, 4);

  tbody.innerHTML = sorted.map(d => `
    <tr>
      <td class="fw-semibold text-break">${d.name}</td>
      <td><span class="badge-custom badge-primary-custom">${d.category}</span></td>
      <td class="fw-bold">${d.recordsCount * 12} times</td>
      <td><span class="badge-custom badge-success-custom">Optimized</span></td>
    </tr>
  `).join('');
  lucide.createIcons();
}

// 13. ACTIVITY LOGS PAGE
function initLogs() {
  const search = document.getElementById('logs-search');
  const modFilter = document.getElementById('logs-filter-module');
  const levelFilter = document.getElementById('logs-filter-status');
  const resetBtn = document.getElementById('logs-reset-filters');
  const csvBtn = document.getElementById('logs-export-btn');

  if (!search) return;

  const filterLogs = () => {
    const q = search.value.toLowerCase().trim();
    const mod = modFilter.value;
    const level = levelFilter.value;

    const filtered = appState.logs.filter(l => {
      const qMatch = l.action.toLowerCase().includes(q) || l.details.toLowerCase().includes(q) || l.user.toLowerCase().includes(q);
      const modMatch = mod === 'All' || l.module === mod.split(' ')[0];
      const levelMatch = level === 'All' || l.status === level;

      return qMatch && modMatch && levelMatch;
    });

    const tbody = document.getElementById('logs-tbody');
    if (tbody) {
      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No audit logs found matching criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(l => `
        <tr>
          <td class="text-muted font-monospace" style="font-size:0.8rem;">${l.timestamp}</td>
          <td class="fw-semibold">${l.user}</td>
          <td><span class="badge bg-secondary-subtle text-secondary px-2">${l.module}</span></td>
          <td class="fw-semibold">${l.action}</td>
          <td>
            <span class="badge-custom ${l.status === 'Success' ? 'badge-success-custom' : l.status === 'Warning' ? 'badge-warning-custom' : 'badge-error-custom'}">
              ${l.status}
            </span>
          </td>
          <td class="text-muted text-break" style="font-size:0.85rem;">${l.details}</td>
        </tr>
      `).join('');
      lucide.createIcons();
    }
  };

  search.addEventListener('input', filterLogs);
  [modFilter, levelFilter].forEach(f => f.addEventListener('change', filterLogs));
  
  if (resetBtn) {
    resetBtn.onclick = () => {
      search.value = '';
      modFilter.value = 'All';
      levelFilter.value = 'All';
      filterLogs();
    };
  }

  if (csvBtn) {
    csvBtn.onclick = () => {
      const csvRows = ['Timestamp,User,Module,Action,Status,Details'];
      appState.logs.forEach(l => {
        csvRows.push(`${l.timestamp},${l.user},${l.module},${l.action},${l.status},"${l.details.replace(/"/g, '""')}"`);
      });
      const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audit_system_logs.csv';
      a.click();
      URL.revokeObjectURL(url);
    };
  }

  filterLogs();
}

// 14. USER MANAGEMENT PAGE
function initUsers() {
  const form = document.getElementById('invite-user-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const fullname = document.getElementById('invite-fullname').value;
      const email = document.getElementById('invite-email').value;
      const role = document.getElementById('invite-role').value;

      appState.users.push({
        name: fullname,
        email: email,
        role: role,
        status: 'Active',
        active: 'Just Joined',
        permissions: role === 'Super Admin' ? 'Full Access' : role === 'Admin' ? 'Write/Queue Access' : 'Read-only',
        avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=100&q=80'
      });
      saveState();
      
      addAuditLog('User', 'Invite Member', `Invited ${fullname} as ${role}.`);
      addNotification(`User invited: ${fullname}`);

      form.reset();
      const modalEl = document.getElementById('inviteUserModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      renderUsersTable();
    });
  }

  renderUsersTable();
}

function renderUsersTable() {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;

  tbody.innerHTML = appState.users.map((u, index) => `
    <tr>
      <td>
        <div class="d-flex align-items-center">
          <img src="${u.avatar}" alt="${u.name}" class="avatar-img me-2">
          <span class="fw-semibold">${u.name}</span>
        </div>
      </td>
      <td><code>${u.email}</code></td>
      <td><span class="badge bg-dark text-white">${u.role}</span></td>
      <td>
        <div class="form-check form-switch">
          <input class="form-check-input" type="checkbox" role="switch" ${u.status === 'Active' ? 'checked' : ''} onclick="toggleUserStatus(${index})">
        </div>
      </td>
      <td class="text-muted" style="font-size:0.8rem;">${u.active}</td>
      <td style="font-size:0.85rem;"><span class="text-muted">${u.permissions}</span></td>
      <td>
        <button class="btn btn-outline-danger btn-sm px-2" onclick="removeUser(${index})" ${u.role === 'Super Admin' ? 'disabled' : ''}>
          <i data-lucide="trash" style="width:14px; height:14px;"></i>
        </button>
      </td>
    </tr>
  `).join('');
  lucide.createIcons();
}

window.toggleUserStatus = function(idx) {
  const user = appState.users[idx];
  if (user) {
    user.status = user.status === 'Active' ? 'Inactive' : 'Active';
    user.active = 'Just Now';
    saveState();
    addAuditLog('User', 'Toggle Status', `Changed user status of ${user.name} to ${user.status}.`);
    renderUsersTable();
  }
};

window.removeUser = function(idx) {
  const user = appState.users[idx];
  if (confirm(`Remove collaborator ${user.name}?`)) {
    appState.users.splice(idx, 1);
    saveState();
    addAuditLog('User', 'Delete Member', `Deleted user account ${user.name}.`);
    renderUsersTable();
  }
};

// 15. SETTINGS PAGE
function initSettings() {
  const saveBtn = document.getElementById('settings-save-btn');
  const copyBtn = document.getElementById('copy-api-key-btn');
  const revealBtn = document.getElementById('reveal-api-key-btn');

  const orgNameInput = document.getElementById('set-org-name');
  const timezoneSelect = document.getElementById('set-sys-timezone');
  const ocrEngineSelect = document.getElementById('set-ocr-engine');
  const llmModelSelect = document.getElementById('set-llm-model');
  const autoSyncCheck = document.getElementById('sync-auto');
  const validationCheck = document.getElementById('sync-validation');
  const webhookUrlInput = document.getElementById('set-webhook-url');
  
  if (orgNameInput && appState.settings) {
    orgNameInput.value = appState.settings.orgName || 'AeroData Dynamics Corp.';
    timezoneSelect.value = appState.settings.timezone || 'IST';
    ocrEngineSelect.value = appState.settings.ocrEngine || 'aws-textract';
    llmModelSelect.value = appState.settings.llmModel || 'gemini-1.5-flash';
    autoSyncCheck.checked = appState.settings.syncAuto !== undefined ? appState.settings.syncAuto : true;
    validationCheck.checked = appState.settings.syncValidation !== undefined ? appState.settings.syncValidation : true;
    webhookUrlInput.value = appState.settings.webhookUrl || 'https://api.aerodata.io/v1/webhooks/excel-sync';
  }

  // Load Excel Schemas fields mapper
  const schemaContainer = document.getElementById('settings-excel-fields-container');
  if (schemaContainer) {
    const fields = [
      { key: 'invoice_number', label: 'Invoice / Ref Number', col: 'C' },
      { key: 'customer_name', label: 'Customer / Vendor Profile', col: 'D' },
      { key: 'invoice_date', label: 'Billing date (YYYY-MM-DD)', col: 'E' },
      { key: 'subtotal_amount', label: 'Subtotal Net Amount', col: 'F' },
      { key: 'tax_amount', label: 'Estimated Taxes Paid', col: 'G' }
    ];
    
    schemaContainer.innerHTML = fields.map(f => `
      <div class="row align-items-center mb-2">
        <div class="col-4">
          <span class="fw-semibold" style="font-size:0.85rem;">${f.label}</span>
        </div>
        <div class="col-4">
          <input type="text" class="form-control form-control-custom font-monospace py-1" value="${f.key}">
        </div>
        <div class="col-1 text-center text-muted">&rarr;</div>
        <div class="col-3">
          <select class="form-select form-select-custom py-1">
            <option value="A">Col A</option>
            <option value="B">Col B</option>
            <option value="C" ${f.col === 'C' ? 'selected' : ''}>Col C</option>
            <option value="D" ${f.col === 'D' ? 'selected' : ''}>Col D</option>
            <option value="E" ${f.col === 'E' ? 'selected' : ''}>Col E</option>
            <option value="F" ${f.col === 'F' ? 'selected' : ''}>Col F</option>
            <option value="G" ${f.col === 'G' ? 'selected' : ''}>Col G</option>
            <option value="H">Col H</option>
          </select>
        </div>
      </div>
    `).join('');
  }

  if (saveBtn) {
    saveBtn.onclick = () => {
      appState.settings = {
        orgName: orgNameInput.value,
        timezone: timezoneSelect.value,
        ocrEngine: ocrEngineSelect.value,
        llmModel: llmModelSelect.value,
        syncAuto: autoSyncCheck.checked,
        syncValidation: validationCheck.checked,
        webhookUrl: webhookUrlInput.value,
        apiKey: document.getElementById('set-api-key').value
      };
      saveState();
      
      addAuditLog('Security', 'Update Settings', 'Saved core parser configuration and schema rules.');
      addNotification('Settings saved successfully');
      alert('System properties have been successfully saved.');
    };
  }

  if (copyBtn) {
    copyBtn.onclick = () => {
      const apiKeyEl = document.getElementById('set-api-key');
      apiKeyEl.select();
      navigator.clipboard.writeText(apiKeyEl.value);
      alert('API Bearer token copied.');
    };
  }

  if (revealBtn) {
    revealBtn.onclick = () => {
      const keyInput = document.getElementById('set-api-key');
      if (keyInput.type === 'password') {
        keyInput.type = 'text';
        revealBtn.innerHTML = '<i data-lucide="eye-off" style="width:16px;"></i> Hide';
      } else {
        keyInput.type = 'password';
        revealBtn.innerHTML = '<i data-lucide="eye" style="width:16px;"></i> Reveal';
      }
      lucide.createIcons();
    };
  }
}
