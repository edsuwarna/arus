/* Login Page — Split Screen Mockup */
function renderLogin() {
  return `
    <div class="login-page show" id="loginPage">
      <div class="login-left">
        <div class="login-logo">
          <span style="display:inline-flex;align-items:center;gap:10px;margin-bottom:20px;">
            <span style="width:36px;height:36px;background:linear-gradient(135deg,#10b981,#059669);border-radius:10px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:18px;color:#fff;">Ar</span>
            <span style="font-size:24px;">Ar<em>us</em></span>
          </span>
        </div>
        <p class="login-tagline">Your data pipeline platform — connect, sync, and orchestrate your data sources effortlessly.</p>
        <form onsubmit="return handleLogin(event)" style="max-width:360px;">
          <div id="loginError" class="login-error" style="display:none"></div>
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="loginEmail" placeholder="your-name@example.com" required>
          </div>
          <div class="form-group">
            <label>Password</label>
            <div class="password-wrap">
              <input type="password" id="loginPassword" placeholder="••••••••" required>
              <button type="button" class="password-toggle" onclick="togglePassword()" title="Toggle password visibility">
                <svg id="eyeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="flex items-center justify-between mb-4">
            <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-secondary);cursor:pointer;">
              <input type="checkbox" checked style="accent-color:var(--emerald);"> Keep me signed in
            </label>
            <a href="#" style="font-size:12px;color:var(--emerald);text-decoration:none;">Forgot password?</a>
          </div>
          <button type="submit" class="btn btn-primary w-full" style="justify-content:center;padding:10px;font-size:14px;" id="loginBtn">Sign in to Arus →</button>
        </form>
        <p style="font-size:12px;color:var(--text-tertiary);margin-top:16px;">
          Don't have an account? <a href="#" style="color:var(--emerald);text-decoration:none;">Request access</a>
        </p>
      </div>
      <div class="login-right">
        <div class="graphic">
          <div class="circle circle-1"></div>
          <div class="circle circle-2"></div>
          <div class="circle circle-3"></div>
          <div class="center-icon">⟁</div>
          <div class="flow-line flow-line-1"></div>
          <div class="flow-line flow-line-2"></div>
        </div>
      </div>
      <div class="login-footer">© 2026 Arus Pipeline. Built for data engineers.</div>
    </div>
  `;
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const btn = document.getElementById('loginBtn');
  const errorEl = document.getElementById('loginError');

  if (!email || !password) {
    errorEl.textContent = 'Please enter email and password';
    errorEl.style.display = 'block';
    return false;
  }

  btn.disabled = true;
  btn.textContent = 'Signing in...';
  errorEl.style.display = 'none';

  try {
    const result = await API.post('/auth/login', { email, password });
    if (result.token) {
      localStorage.setItem('token', result.token);
      App.user = result.user || { email, name: email.split('@')[0], role: 'admin' };
      location.hash = 'dashboard';
      App.render();
    } else {
      throw new Error(result.error || 'Invalid credentials');
    }
  } catch (err) {
    errorEl.textContent = err.message || 'Login failed. Check your credentials.';
    errorEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Sign in to Arus →';
  }
  return false;
}

function togglePassword() {
  const input = document.getElementById('loginPassword');
  const icon = document.getElementById('eyeIcon');
  if (input.type === 'password') {
    input.type = 'text';
    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
  } else {
    input.type = 'password';
    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  }
}
