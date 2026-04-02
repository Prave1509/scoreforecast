console.log('admin_dashboard.js loaded');

// ─── Global State ────────────────────────────────────────────────────────────
let allStudents = [];
let allTeachers = [];
let allPredictions = [];

// ─── Popup (matches your existing .popup style) ───────────────────────────────
function showToast(message, type = 'success') {
  const popup = document.getElementById('popup');
  popup.textContent = message;
  popup.className = 'popup show' + (type === 'error' ? ' error-popup' : '');
  setTimeout(() => { popup.className = 'popup'; }, 3000);
}

// ─── Modal helpers ────────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// Close modals when clicking overlay
document.getElementById('editModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal('editModal');
});
document.getElementById('deleteModal').addEventListener('click', function(e) {
  if (e.target === this) closeModal('deleteModal');
});

document.getElementById('editCancelBtn').addEventListener('click',   () => closeModal('editModal'));
document.getElementById('deleteCancelBtn').addEventListener('click', () => closeModal('deleteModal'));

// ─── Validation helpers ───────────────────────────────────────────────────────

/**
 * Name: letters + spaces only, 2–50 chars, no email/numbers
 */
function validateName(name) {
  const t = name.trim();
  if (t.length < 2 || t.length > 50) return 'Name must be 2–50 characters.';
  if (t.includes('@') || /\.\w{2,}$/.test(t)) return 'Enter a real name, not an email address.';
  if (!/^[\p{L}\s]+$/u.test(t)) return 'Name must contain letters and spaces only.';
  return null; // valid
}

function validatePassword(pw) {
  if (pw.length > 0 && pw.length < 6) return 'Password must be at least 6 characters.';
  return null;
}

function showFieldErr(elId, msg) {
  const el = document.getElementById(elId);
  el.textContent = msg || '';
  el.className   = 'modal-error' + (msg ? ' show' : '');
}

// ─── State for edit/delete ────────────────────────────────────────────────────
let editState  = { type: null, id: null }; // type = 'student' | 'teacher'
let deleteState = { type: null, id: null };

// ─── Fetch & Populate ─────────────────────────────────────────────────────────
async function fetchAndPopulate() {
  showLoading(true);
  try {
    const [stuRes, teaRes, predRes, statsRes] = await Promise.all([
      fetch('/admin/students'),
      fetch('/admin/teachers'),
      fetch('/admin/predictions'),
      fetch('/admin/stats')
    ]);
    const studentsData = await stuRes.json();
    const teachersData = await teaRes.json();
    const predsData    = await predRes.json();
    const statsData    = await statsRes.json();

    allStudents = studentsData.students || [];
    allTeachers = teachersData.teachers || [];
    allPredictions = predsData.predictions || [];

    updateStats(statsData);
    renderChart(statsData);
    populateStudents(allStudents);
    populateTeachers(allTeachers);
    populatePredictions(allPredictions);
  } catch (err) {
    console.error('Error loading admin data', err);
    showToast('Failed to load data from server.', 'error');
  } finally {
    showLoading(false);
  }
}

// ─── Update Stats ────────────────────────────────────────────────────────────
function updateStats(stats) {
  document.getElementById('totalStudents').textContent = stats.students;
  document.getElementById('totalTeachers').textContent = stats.teachers;
  document.getElementById('totalPredictions').textContent = stats.predictions;
}

// ─── Render Chart ────────────────────────────────────────────────────────────
function renderChart(stats) {
  const ctx = document.getElementById('overviewChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Students', 'Teachers', 'Predictions'],
      datasets: [{
        label: 'Count',
        data: [stats.students, stats.teachers, stats.predictions],
        backgroundColor: ['#0d1bd1', '#28a745', '#ffc107'],
        borderColor: ['#0a14a8', '#1e7e34', '#e0a800'],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
}

// ─── Loading Indicator ───────────────────────────────────────────────────────
function showLoading(show) {
  document.getElementById('loadingIndicator').style.display = show ? 'block' : 'none';
}

// ─── Tabs ────────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab + 'Section').classList.add('active');
  });
});

// ─── Search ──────────────────────────────────────────────────────────────────
document.getElementById('studentSearch').addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const filtered = allStudents.filter(s =>
    s.name.toLowerCase().includes(query) || s.student_id.toLowerCase().includes(query)
  );
  populateStudents(filtered);
});

document.getElementById('teacherSearch').addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const filtered = allTeachers.filter(t =>
    t.name.toLowerCase().includes(query) || t.teacher_id.toLowerCase().includes(query)
  );
  populateTeachers(filtered);
});

// ─── Populate functions ───────────────────────────────────────────────────────
function populateStudents(list) {
  const tbody = document.querySelector('#studentsTable tbody');
  document.getElementById('studentCount').textContent = list.length;
  tbody.innerHTML = '';

  if (!list.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No students found.</td></tr>';
    return;
  }

  list.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${s.db_id}</td>
      <td>${escHtml(s.name)}</td>
      <td>${escHtml(s.student_id)}</td>
      <td>
        <button class="btn-edit"   onclick="openEditModal('student','${escAttr(s.student_id)}','${escAttr(s.name)}')">Edit</button>
        <button class="btn-delete" onclick="openDeleteModal('student','${escAttr(s.student_id)}','${escAttr(s.name)}')">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function populateTeachers(list) {
  const tbody = document.querySelector('#teachersTable tbody');
  document.getElementById('teacherCount').textContent = list.length;
  tbody.innerHTML = '';

  if (!list.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No teachers found.</td></tr>';
    return;
  }

  list.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${t.db_id}</td>
      <td>${escHtml(t.name)}</td>
      <td>${escHtml(t.teacher_id)}</td>
      <td>
        <button class="btn-edit"   onclick="openEditModal('teacher','${escAttr(t.teacher_id)}','${escAttr(t.name)}')">Edit</button>
        <button class="btn-delete" onclick="openDeleteModal('teacher','${escAttr(t.teacher_id)}','${escAttr(t.name)}')">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function populatePredictions(list) {
  const tbody = document.querySelector('#predictionsTable tbody');
  document.getElementById('predCount').textContent = list.length;
  tbody.innerHTML = '';

  if (!list.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No predictions found.</td></tr>';
    return;
  }

  list.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${escHtml(p.source)}</td>
      <td>${escHtml(p.user_id || '')}</td>
      <td>${escHtml(p.predicted_mark)}</td>
      <td>${escHtml(p.result)}</td>
      <td>${escHtml(p.timestamp)}</td>`;
    tbody.appendChild(tr);
  });
}

// ─── Edit Modal ───────────────────────────────────────────────────────────────
function openEditModal(type, id, currentName) {
  editState = { type, id };

  document.getElementById('editModalTitle').textContent =
    type === 'student' ? 'Edit Student' : 'Edit Teacher';

  document.getElementById('editName').value     = currentName;
  document.getElementById('editPassword').value = '';
  showFieldErr('editNameError', null);
  showFieldErr('editPassError', null);

  openModal('editModal');
  document.getElementById('editName').focus();
}

document.getElementById('editSaveBtn').addEventListener('click', async () => {
  const name = document.getElementById('editName').value;
  const pw   = document.getElementById('editPassword').value;

  const nameErr = validateName(name);
  const passErr = validatePassword(pw);

  showFieldErr('editNameError', nameErr);
  showFieldErr('editPassError', passErr);

  if (nameErr || passErr) return;

  const body = { name: name.trim() };
  if (pw) body.password = pw;

  const url = editState.type === 'student'
    ? `/admin/student/${editState.id}`
    : `/admin/teacher/${editState.id}`;

  try {
    const res  = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();

    if (res.ok && data.status !== 'error') {
      showToast(`${capitalize(editState.type)} updated successfully.`, 'success');
      closeModal('editModal');
      fetchAndPopulate();
    } else {
      showToast(data.message || 'Update failed.', 'error');
    }
  } catch (err) {
    console.error('Edit error', err);
    showToast('Network error. Could not update.', 'error');
  }
});

// ─── Delete Modal ─────────────────────────────────────────────────────────────
function openDeleteModal(type, id, name) {
  deleteState = { type, id };
  document.getElementById('deleteMsg').textContent =
    `Delete ${type} "${name}" (ID: ${id})? This cannot be undone.`;
  openModal('deleteModal');
}

document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
  const url = deleteState.type === 'student'
    ? `/admin/student/${deleteState.id}`
    : `/admin/teacher/${deleteState.id}`;

  try {
    const res  = await fetch(url, { method: 'DELETE' });
    const data = await res.json();

    if (res.ok && data.status !== 'error') {
      showToast(`${capitalize(deleteState.type)} deleted.`, 'success');
      closeModal('deleteModal');
      fetchAndPopulate();
    } else {
      showToast(data.message || 'Delete failed.', 'error');
    }
  } catch (err) {
    console.error('Delete error', err);
    showToast('Network error. Could not delete.', 'error');
  }
});

// ─── Utils ────────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escAttr(str) {
  return String(str ?? '').replace(/'/g, "\\'");
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ─── Init ─────────────────────────────────────────────────────────────────────
fetchAndPopulate();