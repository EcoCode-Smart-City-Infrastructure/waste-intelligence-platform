/* Waste Intelligence — auth (client-side, zero-build).
 *
 * Email accounts: created and checked in this browser only. Passwords are
 * never stored in plain text — only a SHA-256 hash of (email + password)
 * is kept in localStorage, and the session lives in sessionStorage, so it
 * ends when the browser tab closes. This is a demo-grade local account
 * store, NOT a server account system: accounts do not travel between
 * devices, no verification email is sent, and a real password should
 * never be reused here. See auth-config.js for the shared-account path
 * (Firebase Auth / Auth0 / Supabase).
 *
 * Google / Apple: wired to their real client SDKs, gated by auth-config.js.
 * With no client ID configured (the shipped state), the buttons open the
 * setup panel instead of pretending to sign anyone in.
 */
'use strict';
(function () {
  var ACCOUNTS_KEY = 'wi-accounts-v1';
  var SESSION_KEY = 'wi-session-v1';

  function cfg() { return window.WI_AUTH_CONFIG || {}; }
  function loadAccounts() { try { return JSON.parse(localStorage.getItem(ACCOUNTS_KEY) || '[]'); } catch (e) { return []; } }
  function saveAccounts(a) { localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(a)); }
  function getSession() { try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (e) { return null; } }
  function setSession(s) { if (s) sessionStorage.setItem(SESSION_KEY, JSON.stringify(s)); else sessionStorage.removeItem(SESSION_KEY); }
  function normEmail(e) { return String(e || '').trim().toLowerCase(); }
  function validEmail(e) { return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e); }

  async function sha256Hex(text) {
    if (!window.crypto || !crypto.subtle) throw new Error('This browser cannot hash a password (Web Crypto unavailable).');
    var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map(function (b) { return b.toString(16).padStart(2, '0'); }).join('');
  }
  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) return resolve();
      var s = document.createElement('script'); s.src = src; s.async = true; s.defer = true;
      s.onload = resolve; s.onerror = function () { reject(new Error('Could not load ' + src)); };
      document.head.appendChild(s);
    });
  }
  function showMsg(el, text, ok) {
    if (!el) return; el.textContent = text; el.className = 'auth-msg' + (ok ? ' ok' : ' err'); el.hidden = false;
  }
  function goApp(session) { setSession(session); window.location.href = 'index.html#dashboard'; }

  /* ---------- header chip on index.html ---------- */
  function renderHeader() {
    var link = document.getElementById('authNavLink');
    if (!link) return;
    var s = getSession();
    if (s) {
      link.textContent = 'Signed in: ' + (s.name || s.email);
      link.href = 'login.html';
      var out = document.getElementById('authSignOut');
      if (out) { out.hidden = false; out.onclick = function (e) { e.preventDefault(); setSession(null); window.location.reload(); }; }
    } else {
      link.textContent = 'Sign in'; link.href = 'login.html';
    }
  }

  /* ---------- login page ---------- */
  function setupLoginPage() {
    var signinForm = document.getElementById('signinForm');
    if (!signinForm) return;
    var signupForm = document.getElementById('signupForm');
    var tabSignin = document.getElementById('tabSignin');
    var tabSignup = document.getElementById('tabSignup');
    var setupPanel = document.getElementById('providerSetup');
    var setupText = document.getElementById('providerSetupText');
    var signedBox = document.getElementById('alreadySignedIn');
    var signedText = document.getElementById('alreadySignedInText');

    function showTab(which) {
      signinForm.hidden = which !== 'signin';
      signupForm.hidden = which !== 'signup';
      tabSignin.classList.toggle('active', which === 'signin');
      tabSignup.classList.toggle('active', which === 'signup');
    }
    tabSignin.onclick = function () { showTab('signin'); };
    tabSignup.onclick = function () { showTab('signup'); };
    document.querySelectorAll('[data-show-signup]').forEach(function (el) {
      el.onclick = function (e) { e.preventDefault(); showTab('signup'); };
    });

    var s = getSession();
    if (s) {
      signedText.textContent = 'You are signed in as ' + (s.name || s.email) + ' (' + s.provider + ').';
      signedBox.hidden = false;
      document.getElementById('signOutBtn').onclick = function () { setSession(null); window.location.reload(); };
    }

    signinForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      var email = normEmail(document.getElementById('signinEmail').value);
      var pw = document.getElementById('signinPassword').value;
      var msg = document.getElementById('signinMsg');
      if (!validEmail(email)) return showMsg(msg, 'Enter a valid email address.');
      if (!pw) return showMsg(msg, 'Enter your password.');
      try {
        var hash = await sha256Hex(email + ':' + pw);
        var acc = loadAccounts().find(function (a) { return a.email === email; });
        if (!acc || acc.hash !== hash) return showMsg(msg, 'No account matches that email and password. Create an account, or check the spelling.');
        showMsg(msg, 'Signed in — opening the app…', true);
        goApp({ email: acc.email, name: acc.name, provider: 'email' });
      } catch (err) { showMsg(msg, err.message); }
    });

    signupForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      var name = document.getElementById('signupName').value.trim();
      var email = normEmail(document.getElementById('signupEmail').value);
      var pw = document.getElementById('signupPassword').value;
      var pw2 = document.getElementById('signupPassword2').value;
      var msg = document.getElementById('signupMsg');
      if (!name) return showMsg(msg, 'Enter a display name.');
      if (!validEmail(email)) return showMsg(msg, 'Enter a valid email address.');
      if (pw.length < 8) return showMsg(msg, 'Password must be at least 8 characters.');
      if (pw !== pw2) return showMsg(msg, 'Passwords do not match.');
      var accounts = loadAccounts();
      if (accounts.some(function (a) { return a.email === email; })) return showMsg(msg, 'An account with that email already exists in this browser. Sign in instead.');
      try {
        var hash = await sha256Hex(email + ':' + pw);
        accounts.push({ email: email, name: name, hash: hash, createdAt: new Date().toISOString() });
        saveAccounts(accounts);
        showMsg(msg, 'Account created — opening the app…', true);
        goApp({ email: email, name: name, provider: 'email' });
      } catch (err) { showMsg(msg, err.message); }
    });

    document.querySelectorAll('[data-provider]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var provider = btn.getAttribute('data-provider');
        var msg = document.getElementById('providerMsg');
        setupPanel.hidden = true;
        if (provider === 'google' && !cfg().googleClientId) {
          setupText.innerHTML = '<strong>Google sign-in is not configured yet.</strong> Add a Google OAuth client ID for this Pages origin in <code>auth-config.js</code> (see the steps there), then this button will sign in with Google. No account is created by this button until then.';
          setupPanel.hidden = false; return;
        }
        if (provider === 'apple' && !cfg().appleClientId) {
          setupText.innerHTML = '<strong>Apple sign-in is not configured yet.</strong> Add an Apple Service ID for this page in <code>auth-config.js</code> (see the steps there), then this button will sign in with Apple. No account is created by this button until then.';
          setupPanel.hidden = false; return;
        }
        try {
          if (provider === 'google') await signInGoogle(msg);
          if (provider === 'apple') await signInApple(msg);
        } catch (err) { showMsg(msg, 'Sign-in failed: ' + err.message); }
      });
    });

    async function signInGoogle(msg) {
      await loadScript('https://accounts.google.com/gsi/client');
      return new Promise(function (resolve, reject) {
        var client = google.accounts.oauth2.initTokenClient({
          client_id: cfg().googleClientId, scope: 'openid email profile',
          callback: async function (resp) {
            if (resp.error) return reject(new Error(resp.error));
            try {
              var r = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', { headers: { Authorization: 'Bearer ' + resp.access_token } });
              var u = await r.json();
              if (!u.email) throw new Error('Google did not return an email address.');
              showMsg(msg, 'Signed in with Google — opening the app…', true);
              goApp({ email: normEmail(u.email), name: u.name || u.email, provider: 'google' }); resolve();
            } catch (err) { reject(err); }
          }
        });
        client.requestAccessToken();
      });
    }
    async function signInApple(msg) {
      await loadScript('https://appleid.apple.com/auth/apple.js');
      AppleID.auth.init({ clientId: cfg().appleClientId, scope: 'name email', redirectURI: cfg().appleRedirectUri || window.location.href.split('?')[0].split('#')[0], usePopup: true });
      var resp = await AppleID.auth.signIn();
      var parts = resp.authorization.id_token.split('.');
      var payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      var name = (resp.user && resp.user.name) ? [resp.user.name.firstName, resp.user.name.lastName].filter(Boolean).join(' ') : (payload.email || 'Apple user');
      showMsg(msg, 'Signed in with Apple — opening the app…', true);
      goApp({ email: normEmail(payload.email || ''), name: name, provider: 'apple' });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderHeader();
    setupLoginPage();
  });
  window.WI_AUTH = { getSession: getSession, signOut: function () { setSession(null); } };
})();
