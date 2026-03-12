console.log('admin_dashboard.js loaded');

async function fetchAndPopulate() {
    try {
        const [stuRes, teaRes, predRes] = await Promise.all([
            fetch('/admin/students'),
            fetch('/admin/teachers'),
            fetch('/admin/predictions')
        ]);
        const studentsData = await stuRes.json();
        const teachersData = await teaRes.json();
        const predsData = await predRes.json();
        populateStudents(studentsData.students || []);
        populateTeachers(teachersData.teachers || []);
        populatePredictions(predsData.predictions || []);
    } catch (err) {
        console.error('error loading admin data', err);
        alert('Failed to load data from server.');
    }
}

function populateStudents(list) {
    const tbody = document.querySelector('#studentsTable tbody');
    tbody.innerHTML = '';
    list.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${s.db_id}</td><td>${s.name}</td><td>${s.student_id}</td>
            <td class="actions">
                <button onclick="editStudent('${s.student_id}','${s.name}')">Edit</button>
                <button onclick="deleteStudent('${s.student_id}')">Delete</button>
            </td>`;
        tbody.appendChild(tr);
    });
}

function populateTeachers(list) {
    const tbody = document.querySelector('#teachersTable tbody');
    tbody.innerHTML = '';
    list.forEach(t => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${t.db_id}</td><td>${t.name}</td><td>${t.teacher_id}</td>
            <td class="actions">
                <button onclick="editTeacher('${t.teacher_id}','${t.name}')">Edit</button>
                <button onclick="deleteTeacher('${t.teacher_id}')">Delete</button>
            </td>`;
        tbody.appendChild(tr);
    });
}

function populatePredictions(list) {
    const tbody = document.querySelector('#predictionsTable tbody');
    tbody.innerHTML = '';
    list.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${p.id}</td><td>${p.source}</td><td>${p.user_id || ''}</td><td>${p.predicted_mark}</td><td>${p.result}</td><td>${p.timestamp}</td>`;
        tbody.appendChild(tr);
    });
}

function deleteStudent(id) {
    if (!confirm('Are you sure you want to delete this student?')) return;
    fetch(`/admin/student/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => fetchAndPopulate());
}

function deleteTeacher(id) {
    if (!confirm('Are you sure you want to delete this teacher?')) return;
    fetch(`/admin/teacher/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(() => fetchAndPopulate());
}

function editStudent(id, currentName) {
    const newName = prompt('Enter new name for student', currentName);
    if (newName === null) return; // cancelled
    const newPassword = prompt('Enter new password (leave empty to keep existing)');
    const body = {};
    if (newName) body.name = newName;
    if (newPassword) body.password = newPassword;
    fetch(`/admin/student/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(() => fetchAndPopulate());
}

function editTeacher(id, currentName) {
    const newName = prompt('Enter new name for teacher', currentName);
    if (newName === null) return;
    const newPassword = prompt('Enter new password (leave empty to keep existing)');
    const body = {};
    if (newName) body.name = newName;
    if (newPassword) body.password = newPassword;
    fetch(`/admin/teacher/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(() => fetchAndPopulate());
}

// initial load
fetchAndPopulate();