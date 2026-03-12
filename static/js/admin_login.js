console.log('admin_login.js loaded');
const adminForm = document.getElementById('adminLoginForm');
if (adminForm) {
    adminForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const admin_id = document.getElementById('admin_id').value.trim();
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/admin_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_id, password })
            });
            const data = await response.json();
            console.log('admin login response', data);
            if (data.status === 'success') {
                window.location.href = '/admin_dashboard';
            } else if (data.status === 'invalid') {
                alert('Invalid ID or Password');
            } else {
                alert('An error occurred');
            }
        } catch (err) {
            console.error('network error during admin login', err);
            alert('Could not reach server; is the backend running?');
        }
    });
} else {
    console.warn('admin login form element not found');
}