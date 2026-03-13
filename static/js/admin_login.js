console.log('admin_login.js loaded');

// ─── Validation Helpers ───────────────────────────────────────────────────────

/**
 * Name rules:
 *  - 3 to 30 characters
 *  - Letters (including Tamil/Unicode letters) and spaces ONLY
 *  - NO digits, NO email symbols (@, .), NO special chars
 */
function validateAdminName(name) {
  const trimmed = name.trim();

  if (trimmed.length < 3 || trimmed.length > 30) {
    return { ok: false, msg: 'Name must be 3–30 characters long.' };
  }

  // Reject if it looks like an email
  if (trimmed.includes('@') || /\.\w{2,}$/.test(trimmed)) {
    return { ok: false, msg: 'Enter a name, not an email address.' };
  }

  // Allow only letters (any language) and spaces
  if (!/^[\p{L}\s]+$/u.test(trimmed)) {
    return { ok: false, msg: 'Name must contain letters and spaces only — no numbers or symbols.' };
  }

  return { ok: true };
}

/**
 * Password rules:
 *  - At least 6 characters
 *  - Not entirely whitespace
 */
function validatePassword(password) {
  if (!password || password.trim().length === 0) {
    return { ok: false, msg: 'Password cannot be empty.' };
  }
  if (password.length < 6) {
    return { ok: false, msg: 'Password must be at least 6 characters.' };
  }
  return { ok: true };
}

// ─── UI Helpers ──────────────────────────────────────────────────────────────

function showFieldError(inputEl, msgEl, message) {
  inputEl.classList.add('error');
  msgEl.textContent = message;
  msgEl.classList.add('show');
}

function clearFieldError(inputEl, msgEl) {
  inputEl.classList.remove('error');
  msgEl.classList.remove('show');
}

function showAlert(message) {
  const box = document.getElementById('alertBox');
  box.textContent = message;
  box.className = 'alert error';
}

function clearAlert() {
  const box = document.getElementById('alertBox');
  box.className = 'alert';
  box.textContent = '';
}

// ─── Live Validation (as user types) ─────────────────────────────────────────

const nameInput  = document.getElementById('admin_id');
const passInput  = document.getElementById('password');
const nameError  = document.getElementById('nameError');
const passError  = document.getElementById('passError');

nameInput.addEventListener('input', () => {
  const result = validateAdminName(nameInput.value);
  if (!result.ok) {
    showFieldError(nameInput, nameError, result.msg);
  } else {
    clearFieldError(nameInput, nameError);
  }
});

passInput.addEventListener('input', () => {
  const result = validatePassword(passInput.value);
  if (!result.ok) {
    showFieldError(passInput, passError, result.msg);
  } else {
    clearFieldError(passInput, passError);
  }
});

// ─── Form Submit ─────────────────────────────────────────────────────────────

const adminForm = document.getElementById('adminLoginForm');
const loginBtn  = document.getElementById('loginBtn');

if (adminForm) {
  adminForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearAlert();

    const admin_id = nameInput.value.trim();
    const password = passInput.value;

    // Run validations
    const nameResult = validateAdminName(admin_id);
    const passResult = validatePassword(password);

    let hasError = false;

    if (!nameResult.ok) {
      showFieldError(nameInput, nameError, nameResult.msg);
      hasError = true;
    } else {
      clearFieldError(nameInput, nameError);
    }

    if (!passResult.ok) {
      showFieldError(passInput, passError, passResult.msg);
      hasError = true;
    } else {
      clearFieldError(passInput, passError);
    }

    if (hasError) return;

    // Send to server
    loginBtn.disabled = true;
    loginBtn.textContent = 'Verifying...';

    try {
      const response = await fetch('/admin_login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_id, password })
      });

      const data = await response.json();
      console.log('admin login response', data);

      if (data.status === 'success') {
        loginBtn.textContent = 'Redirecting...';
        window.location.href = '/admin_dashboard';
      } else if (data.status === 'invalid') {
        showAlert('Invalid admin name or password. Please try again.');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
      } else {
        showAlert('An unexpected error occurred. Please try again.');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
      }

    } catch (err) {
      console.error('Network error during admin login', err);
      showAlert('Could not reach the server. Is the backend running?');
      loginBtn.disabled = false;
      loginBtn.textContent = 'Login';
    }
  });

} else {
  console.warn('Admin login form element not found');
}