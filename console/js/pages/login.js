/* Login Page — Split Screen Mockup */
function renderLogin() {
  return `
    <div class="login-page show" id="loginPage">
      <div class="login-left">
        <div class="login-logo">
            <span style="display:inline-flex;align-items:center;gap:10px;margin-bottom:20px;">
              <svg width="36" height="36" viewBox="0 0 32 32" fill="none" style="flex-shrink:0">
                <rect x="1" y="1" width="30" height="30" rx="7" fill="#14171d" stroke="#23262e" stroke-width="0.5"/>
                <polyline points="8,10 12,14 8,18" stroke="#eab308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                <polyline points="14,10 18,14 14,18" stroke="#ca8a04" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.6"/>
                <polyline points="20,10 24,14 20,18" stroke="#a16207" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.3"/>
              </svg>
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
        <p style="font-size:12px;color:var(--text-secondary);margin-top:16px;">
          Don't have an account? <a href="#" style="color:var(--emerald);text-decoration:none;">Request access</a>
        </p>
      </div>
      <div class="login-right">
        <svg class="login-graphic" viewBox="0 0 400 420" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="dg" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="12" cy="12" r="1" fill="#23262e" opacity="0.4"/>
            </pattern>
            <linearGradient id="arrowGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#2a2d35"/>
              <stop offset="80%" stop-color="#eab308"/>
              <stop offset="100%" stop-color="#eab308"/>
            </linearGradient>
            <linearGradient id="waveGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#eab308" stop-opacity="0"/>
              <stop offset="25%" stop-color="#eab308" stop-opacity="0.25"/>
              <stop offset="50%" stop-color="#ca8a04" stop-opacity="0.5"/>
              <stop offset="75%" stop-color="#eab308" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="#eab308" stop-opacity="0"/>
            </linearGradient>
            <linearGradient id="nodeSrc" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#1a1d24"/>
              <stop offset="100%" stop-color="#14171d"/>
            </linearGradient>
            <filter id="nodeGlow">
              <feGaussianBlur stdDeviation="6" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="particleGlow">
              <feGaussianBlur stdDeviation="2"/>
            </filter>
          </defs>

          <!-- Grid bg -->
          <rect width="400" height="420" fill="url(#dg)"/>

          <!-- Subtle radial glow center -->
          <radialGradient id="centerGlow" cx="0.5" cy="0.45" r="0.5">
            <stop offset="0%" stop-color="#eab308" stop-opacity="0.04"/>
            <stop offset="100%" stop-color="#eab308" stop-opacity="0"/>
          </radialGradient>
          <circle cx="200" cy="190" r="180" fill="url(#centerGlow)"/>

          <!-- Title -->
          <text x="200" y="45" text-anchor="middle" fill="#e8eaed" font-size="22" font-weight="700" font-family="Inter,sans-serif" letter-spacing="-0.3">Data <tspan fill="#eab308">Flow</tspan> Platform</text>
          <text x="200" y="65" text-anchor="middle" fill="#9aa0a8" font-size="11" font-family="Inter,sans-serif">Real-time CDC pipeline orchestration</text>

          <!-- ============ CONNECTING ARROWS ============ -->
          <!-- Source → Pipeline -->
          <path d="M125,175 L175,175" stroke="url(#arrowGrad)" stroke-width="1.5" stroke-dasharray="4,3"/>
          <polygon points="175,171 182,175 175,179" fill="#eab308"/>
          <!-- Pipeline → Target -->
          <path d="M225,175 L275,175" stroke="url(#arrowGrad)" stroke-width="1.5" stroke-dasharray="4,3"/>
          <polygon points="275,171 282,175 275,179" fill="#eab308"/>

          <!-- ============ NODE: SOURCE (LEFT) ============ -->
          <g>
            <rect x="38" y="138" width="84" height="74" rx="10" fill="url(#nodeSrc)" stroke="#2a2d35" stroke-width="1"/>
            <text x="80" y="156" text-anchor="middle" fill="#9aa0a8" font-size="8" font-weight="600" font-family="Inter,sans-serif" letter-spacing="1">SOURCE</text>
            <!-- Cylinder / DB icon -->
            <ellipse cx="80" cy="184" rx="16" ry="5" fill="none" stroke="#9aa0a8" stroke-width="1.3"/>
            <path d="M64,184 L64,192 C64,195 71.2,197 80,197 C88.8,197 96,195 96,192 L96,184" fill="none" stroke="#9aa0a8" stroke-width="1.3"/>
            <ellipse cx="80" cy="192" rx="16" ry="5" fill="none" stroke="#9aa0a8" stroke-width="1.3"/>
          </g>

          <!-- ============ NODE: CDC PIPELINE (CENTER, HIGHLIGHTED) ============ -->
          <g filter="url(#nodeGlow)">
            <rect x="174" y="125" width="52" height="100" rx="12" fill="#1a1d24" stroke="rgba(234,179,8,0.3)" stroke-width="1"/>
            <rect x="176" y="127" width="48" height="96" rx="10" fill="rgba(234,179,8,0.04)" stroke="rgba(234,179,8,0.1)" stroke-width="0.5"/>
            <text x="200" y="145" text-anchor="middle" fill="#eab308" font-size="7.5" font-weight="700" font-family="Inter,sans-serif" letter-spacing="0.8">CDC</text>
            <text x="200" y="155" text-anchor="middle" fill="#eab308" font-size="7.5" font-weight="700" font-family="Inter,sans-serif" letter-spacing="0.8">PIPELINE</text>
            <!-- Gear/flow icon -->
            <g transform="translate(200,182)" opacity="0.8">
              <circle cx="0" cy="0" r="12" fill="none" stroke="#eab308" stroke-width="1.3"/>
              <circle cx="0" cy="0" r="4" fill="#eab308" opacity="0.6"/>
              <path d="M-8,-8 L8,8" stroke="#eab308" stroke-width="1.3" stroke-linecap="round" opacity="0.4"/>
              <path d="M-8,8 L8,-8" stroke="#eab308" stroke-width="1.3" stroke-linecap="round" opacity="0.4"/>
            </g>
          </g>

          <!-- ============ NODE: TARGET (RIGHT) ============ -->
          <g>
            <rect x="278" y="138" width="84" height="74" rx="10" fill="url(#nodeSrc)" stroke="#2a2d35" stroke-width="1"/>
            <text x="320" y="156" text-anchor="middle" fill="#9aa0a8" font-size="8" font-weight="600" font-family="Inter,sans-serif" letter-spacing="1">TARGET</text>
            <!-- Warehouse stack icon -->
            <rect x="306" y="174" width="28" height="18" rx="3" fill="none" stroke="#9aa0a8" stroke-width="1.3"/>
            <rect x="309" y="177" width="22" height="12" rx="2" fill="none" stroke="#9aa0a8" stroke-width="1" opacity="0.5"/>
            <rect x="312" y="180" width="16" height="6" rx="1.5" fill="none" stroke="#9aa0a8" stroke-width="0.8" opacity="0.3"/>
          </g>

          <!-- ============ WAVE LINES (BOTTOM) ============ -->
          <g opacity="0.7">
            <path d="M-10,300 Q40,288 90,300 T190,300 T290,300 T390,300 T410,300" stroke="url(#waveGrad)" stroke-width="1.5" fill="none" class="wave-1"/>
            <path d="M-10,318 Q40,308 90,318 T190,318 T290,318 T390,318 T410,318" stroke="url(#waveGrad)" stroke-width="1" fill="none" opacity="0.5" class="wave-2"/>
            <path d="M-10,334 Q40,326 90,334 T190,334 T290,334 T390,334 T410,334" stroke="url(#waveGrad)" stroke-width="0.8" fill="none" opacity="0.3" class="wave-3"/>
            <path d="M-10,348 Q40,342 90,348 T190,348 T290,348 T390,348 T410,348" stroke="url(#waveGrad)" stroke-width="0.5" fill="none" opacity="0.15" class="wave-4"/>
          </g>

          <!-- ============ ANIMATED PARTICLES ============ -->
          <circle r="2.5" fill="#eab308" opacity="0.8" filter="url(#particleGlow)">
            <animateMotion dur="4s" repeatCount="indefinite" path="M125,175 L175,175"/>
          </circle>
          <circle r="2" fill="#ca8a04" opacity="0.6" filter="url(#particleGlow)">
            <animateMotion dur="4s" repeatCount="indefinite" path="M225,175 L275,175" begin="1s"/>
          </circle>
          <circle r="2" fill="#eab308" opacity="0.5" filter="url(#particleGlow)">
            <animateMotion dur="6s" repeatCount="indefinite" path="M40,300 Q90,288 140,300 Q190,312 240,300 Q290,288 340,300 Q390,312 410,300" begin="0.5s"/>
          </circle>
          <circle r="1.5" fill="#ca8a04" opacity="0.4" filter="url(#particleGlow)">
            <animateMotion dur="6s" repeatCount="indefinite" path="M40,318 Q90,308 140,318 Q190,328 240,318 Q290,308 340,318 Q390,328 410,318" begin="2s"/>
          </circle>
        </svg>
        <div class="login-footer">© 2026 Arus Pipeline. Built for data engineers.</div>
      </div>
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
    if (result.access_token) {
      localStorage.setItem('access_token', result.access_token);
      if (result.refresh_token) localStorage.setItem('refresh_token', result.refresh_token);
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
