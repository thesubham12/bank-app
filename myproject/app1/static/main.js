// ── Dark Mode Toggle ──
(function () {
  const toggleBtn = document.getElementById('themeToggleBtn');
  const toggleIcon = document.getElementById('themeToggleIcon');
  if (!toggleBtn) return;

  function applyTheme(isDark) {
    document.body.classList.toggle('dark-theme', isDark);
    toggleIcon.className = isDark ? 'ti ti-sun' : 'ti ti-moon';
  }

  const saved = localStorage.getItem('apexbank_theme');
  applyTheme(saved === 'dark');

  toggleBtn.addEventListener('click', function () {
    const isDark = !document.body.classList.contains('dark-theme');
    applyTheme(isDark);
    localStorage.setItem('apexbank_theme', isDark ? 'dark' : 'light');
  });
})();


/* ── Password toggle (used in register.html & login.html) ── */
function togglePassword(id, icon) {
    const field = document.getElementById(id);
    if (field.type === 'password') {
        field.type = 'text';
        icon.innerHTML = '🙈';
    } else {
        field.type = 'password';
        icon.innerHTML = '👁️';
    }
}

/* ============================================================
   ACCOUNT TYPE SELECTION PAGE
   ============================================================ */

let selectedCard = null;

function selectCard(card) {
    document.querySelectorAll('.acc-card').forEach(c => {
        if (c !== card) c.classList.remove('selected');
    });
    card.classList.add('selected');
    selectedCard = card;
    const label = document.getElementById('selected-label');
    const name  = card.dataset.account;
    label.textContent = '✓ Selected: ' + name;
    const btn = document.getElementById('proceed-btn');
    btn.disabled = false;
}

function proceedToOpen() {
    if(!selectedCard) {
        alert("Please select an account type first");
        return;
    }
    const accountType = selectedCard.dataset.account;
    if(accountType === "Savings Account"){
        const btn = document.getElementById('proceed-btn');
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Opening...';
        btn.disabled = true;
        window.location.href = "/app2/saving_ac_create/";
    } else {
    document.getElementById('unavailableAccountType').textContent = accountType;
    const modal = new bootstrap.Modal(document.getElementById('serviceUnavailableModal'));
    modal.show();
}
}

if(document.getElementById('photo-upload')) {
    document.getElementById('photo-upload').addEventListener('change', function () {
        const file = this.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById('avatar-preview').src = e.target.result;
        };
        reader.readAsDataURL(file);
        setTimeout(() => document.getElementById('photo-form').submit(), 400);
    });
}

document.querySelectorAll('.toast').forEach(el => {
    new bootstrap.Toast(el, { delay: 3500 }).show();
});

window.addEventListener('load', function() {
    const params = new URLSearchParams(window.location.search);
    const open = params.get('open');
    if (open === 'deposit') {
        new bootstrap.Modal(document.getElementById('depositModal')).show();
    } else if (open === 'withdraw') {
        new bootstrap.Modal(document.getElementById('withdrawModal')).show();
    }
});


/* ─────────────────────────────────────────────
   support.js  —  Apex Bank Support Page
   ───────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', function () {

  /* 1. SCROLL REVEAL */
  const revealEls = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => entry.target.classList.add('visible'), i * 60);
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealEls.forEach(el => revealObserver.observe(el));

  /* 2. FAQ ACCORDION */
  document.querySelectorAll('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const item   = btn.parentElement;
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  /* 3. LIVE CHAT DEMO */
  const agentReplies = [
    'Of course! I can help you with that right away.',
    'Could you please share your account number so I can look into this?',
    'I can see your account details. Let me check this for you.',
    'This is resolved now! Is there anything else I can help you with?',
    'Thank you for banking with Apex Bank. Have a great day! 😊',
  ];
  let replyIndex = 0;

  function addMessage(text, type) {
    const msgs = document.getElementById('chatMessages');
    if (!msgs) return;
    const div = document.createElement('div');
    div.className = 'msg ' + type;
    div.innerHTML = `
      <div class="msg-bubble">${text}</div>
      <div class="msg-time">Just now</div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function showTyping() {
    const msgs = document.getElementById('chatMessages');
    if (!msgs) return null;
    const div = document.createElement('div');
    div.className = 'msg agent typing-indicator';
    div.innerHTML = `
      <div class="msg-bubble">
        <div class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function sendChat() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    const typingEl = showTyping();
    setTimeout(() => {
      if (typingEl) typingEl.remove();
      const reply = agentReplies[replyIndex % agentReplies.length];
      replyIndex++;
      addMessage(reply, 'agent');
    }, 1200);
  }

  const sendBtn   = document.getElementById('sendBtn');
  const chatInput = document.getElementById('chatInput');

  if (sendBtn)   sendBtn.addEventListener('click', sendChat);
  if (chatInput) chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') sendChat();
  });

  /* 4. CONTACT / SUPPORT FORM */
  const submitBtn    = document.getElementById('submitBtn');
  const successToast = document.getElementById('successToast');

  if (submitBtn) {
    submitBtn.addEventListener('click', () => {
      const name  = document.getElementById('fname')?.value.trim();
      const email = document.getElementById('email')?.value.trim();
      const desc  = document.getElementById('desc')?.value.trim();

      if (!name || !email || !desc) {
        alert('Please fill in Name, Email, and Description.');
        return;
      }

      if (successToast) successToast.classList.add('show');
      submitBtn.disabled      = true;
      submitBtn.style.opacity = '0.6';

      setTimeout(() => {
        if (successToast) successToast.classList.remove('show');
        submitBtn.disabled      = false;
        submitBtn.style.opacity = '1';
        ['fname', 'email', 'accno', 'phone', 'desc'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.value = '';
        });
        const category = document.getElementById('category');
        if (category) category.value = '';
      }, 4000);
    });
  }

});

// Sticky navbar shadow on scroll
window.addEventListener('scroll', function () {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        if (window.scrollY > 10) {
            navbar.style.boxShadow = '0 4px 20px rgba(0, 51, 102, 0.2)';
        } else {
            navbar.style.boxShadow = '0 2px 12px rgba(0, 51, 102, 0.12)';
        }
    }
});
/* ── Balance eye toggle (profile page) ── */
function toggleBalance() {
  const eyeIcon   = document.getElementById('balanceEyeIcon');
  const balanceEl = document.getElementById('balanceAmount');
  const eyeBtn    = document.getElementById('balanceEyeBtn');
  if (!eyeIcon || !balanceEl) return;

  const realBalance = balanceEl.dataset.balance;
  const isHidden    = balanceEl.textContent.trim() === '₹••••••';

  if (isHidden) {
    balanceEl.textContent = realBalance;
    eyeIcon.classList.remove('ti-eye-off');
    eyeIcon.classList.add('ti-eye');
    if (eyeBtn) eyeBtn.title = 'Hide balance';
  } else {
    balanceEl.textContent = '₹••••••';
    eyeIcon.classList.remove('ti-eye');
    eyeIcon.classList.add('ti-eye-off');
    if (eyeBtn) eyeBtn.title = 'Show balance';
  }
}


// search bar code

const searchItems = [
    { name: "Deposit Money", action: 'modal', modalId: 'depositModal' },
    { name: "Withdraw Money", action: 'modal', modalId: 'withdrawModal' },
    { name: "Transfer Funds", url: window.transferUrl },
    { name: "Check Balance", url: window.profileUrl },
    { name: "Download Statement", url: window.transactionHistoryUrl },
    { name: "Customer Support", url: window.supportUrl },
];

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('siteSearchInput');
    const results = document.getElementById('searchResults');

    if (!input || !results) return;

    input.addEventListener('input', function () {
        const query = this.value.trim().toLowerCase();
        results.innerHTML = '';

        if (query === '') {
            results.style.display = 'none';
            return;
        }

        const matches = searchItems.filter(item =>
            item.name.toLowerCase().includes(query)
        );

        if (matches.length === 0) {
            results.style.display = 'none';
            return;
        }

        matches.forEach(item => {
            const div = document.createElement('div');
            div.textContent = item.name;
            div.style.padding = '8px 12px';
            div.style.cursor = 'pointer';
            div.addEventListener('click', () => {
                if (item.action === 'modal') {
                    const modalId = item.modalId; // e.g., 'depositModal'
                    const modal = new bootstrap.Modal(document.getElementById(modalId));
                    modal.show();
                } else {
                    // For others, navigate to URL
                    window.location.href = item.url;
                }
            });
            results.appendChild(div);
        });

        results.style.display = 'block';
    });

    document.addEventListener('click', function (e) {
        if (!results.contains(e.target) && e.target !== input) {
            results.style.display = 'none';
        }
    });
});

// verify otp 
let secs = 30;
  const countEl   = document.getElementById('timerCount');
  const timerTxt  = document.getElementById('timerTxt');
  const expiredTxt= document.getElementById('expiredTxt');
  const verifyBtn = document.getElementById('verifyBtn');
  const resendForm= document.getElementById('resendForm');

  const interval = setInterval(() => {
    secs--;
    countEl.textContent = secs;
    if (secs <= 0) {
      clearInterval(interval);
      timerTxt.style.display   = 'none';
      expiredTxt.style.display = 'inline';
      verifyBtn.disabled       = true;
      verifyBtn.style.opacity  = '0.5';
      resendForm.style.display = 'block';  // Resend button dikhao
    }
  }, 1000);

// ---------------------
// profile page

(function () {
  const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
  if (!csrfEl) return;
  const CSRF = csrfEl.value;

  function post(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(body)
    }).then(r => r.json());
  }

  function showErr(el, msg) { el.textContent = msg; el.classList.remove('d-none'); }
  function hideErr(el)      { el.classList.add('d-none'); }

  // ── reset modal to step 1 when it closes ──
  ['changePasswordModal','changeMpinModal','changeTpinModal'].forEach(id => {
    document.getElementById(id)?.addEventListener('hidden.bs.modal', () => {
      resetModal(id);
    });
  });

  function resetModal(id) {
    if (id === 'changePasswordModal') {
      stopTimer('pw');
      ['pw_old','pw_new','pw_confirm','pw_otp'].forEach(i => { const el=document.getElementById(i); if(el) el.value=''; });
      document.getElementById('pwStep1').classList.remove('d-none');
      document.getElementById('pwStep2').classList.add('d-none');
      document.getElementById('pwStep1Btn').classList.remove('d-none');
      document.getElementById('pwStep2Btn').classList.add('d-none');
      hideErr(document.getElementById('pwErr1'));
      hideErr(document.getElementById('pwErr2'));
    } else if (id === 'changeMpinModal') {
      stopTimer('mpin');
      ['mpin_new','mpin_confirm','mpin_otp'].forEach(i => { const el=document.getElementById(i); if(el) el.value=''; });
      document.getElementById('mpinStep1').classList.remove('d-none');
      document.getElementById('mpinStep2').classList.add('d-none');
      document.getElementById('mpinStep1Btn').classList.remove('d-none');
      document.getElementById('mpinStep2Btn').classList.add('d-none');
      hideErr(document.getElementById('mpinErr1'));
      hideErr(document.getElementById('mpinErr2'));
    } else if (id === 'changeTpinModal') {
      stopTimer('tpin');
      ['tpin_new','tpin_confirm','tpin_otp'].forEach(i => { const el=document.getElementById(i); if(el) el.value=''; });
      document.getElementById('tpinStep1').classList.remove('d-none');
      document.getElementById('tpinStep2').classList.add('d-none');
      document.getElementById('tpinStep1Btn').classList.remove('d-none');
      document.getElementById('tpinStep2Btn').classList.add('d-none');
      hideErr(document.getElementById('tpinErr1'));
      hideErr(document.getElementById('tpinErr2'));
    }
  }

  // ── countdown timer ──
  const timers = {};   // keyed by prefix: 'pw' | 'mpin' | 'tpin'

  function startTimer(prefix) {
    clearInterval(timers[prefix]);
    const countEl  = document.getElementById(prefix + 'TimerCount');
    const timerTxt = document.getElementById(prefix + 'TimerTxt');
    const resendBtn= document.getElementById(prefix + 'ResendBtn');
    let   secs     = 30;

    // reset UI
    if (countEl)   countEl.textContent = secs;
    if (timerTxt)  timerTxt.classList.remove('d-none');
    if (resendBtn) resendBtn.classList.add('d-none');

    timers[prefix] = setInterval(() => {
      secs--;
      if (countEl) countEl.textContent = secs;
      if (secs <= 0) {
        clearInterval(timers[prefix]);
        if (timerTxt)  timerTxt.classList.add('d-none');
        if (resendBtn) resendBtn.classList.remove('d-none');
      }
    }, 1000);
  }

  function stopTimer(prefix) {
    clearInterval(timers[prefix]);
    const timerTxt = document.getElementById(prefix + 'TimerTxt');
    const resendBtn= document.getElementById(prefix + 'ResendBtn');
    if (timerTxt)  timerTxt.classList.add('d-none');
    if (resendBtn) resendBtn.classList.add('d-none');
  }

  // ── helper: go to step 2 ──
  function toStep2(step1El, step2El, s1Btn, s2Btn, maskedEl, maskedEmail, prefix) {
    step1El.classList.add('d-none');
    step2El.classList.remove('d-none');
    s1Btn.classList.add('d-none');
    s2Btn.classList.remove('d-none');
    maskedEl.textContent = maskedEmail;
    startTimer(prefix);
  }

  // ══════════════════════════
  //  PASSWORD
  // ══════════════════════════
  function sendPasswordOTP() {
    const err = document.getElementById('pwErr1');
    hideErr(err);
    const btn = document.getElementById('pwStep1Btn');
    btn.disabled = true; btn.textContent = 'Sending…';

    post('/app2/send-change-otp/', {
      action: 'password',
      old_password:     document.getElementById('pw_old').value,
      new_password:     document.getElementById('pw_new').value,
      confirm_password: document.getElementById('pw_confirm').value
    }).then(res => {
      btn.disabled = false; btn.textContent = 'Send OTP';
      if (res.ok) {
        toStep2(
          document.getElementById('pwStep1'),
          document.getElementById('pwStep2'),
          document.getElementById('pwStep1Btn'),
          document.getElementById('pwStep2Btn'),
          document.getElementById('pwMaskedEmail'),
          res.masked_email,
          'pw'
        );
      } else {
        showErr(err, res.error);
      }
    }).catch(() => { btn.disabled=false; btn.textContent='Send OTP'; showErr(err,'Network error. Try again.'); });
  }

  document.getElementById('pwStep1Btn')?.addEventListener('click', sendPasswordOTP);
  document.getElementById('pwResendBtn')?.addEventListener('click', () => {
    stopTimer('pw');
    document.getElementById('pwStep2').classList.add('d-none');
    document.getElementById('pwStep1').classList.remove('d-none');
    document.getElementById('pwStep1Btn').classList.remove('d-none');
    document.getElementById('pwStep2Btn').classList.add('d-none');
    sendPasswordOTP();
  });

  document.getElementById('pwStep2Btn')?.addEventListener('click', () => {
    const err = document.getElementById('pwErr2');
    hideErr(err);
    const btn = document.getElementById('pwStep2Btn');
    btn.disabled = true; btn.textContent = 'Verifying…';

    post('/app2/verify-change-otp/', { otp: document.getElementById('pw_otp').value })
      .then(res => {
        btn.disabled = false; btn.textContent = 'Update Password';
        if (res.ok) {
          bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
          showToast(res.message || 'Password updated!', 'success');
        } else {
          showErr(err, res.error);
        }
      }).catch(() => { btn.disabled=false; btn.textContent='Update Password'; showErr(err,'Network error.'); });
  });

  // ══════════════════════════
  //  MPIN
  // ══════════════════════════
  function sendMpinOTP() {
    const err = document.getElementById('mpinErr1');
    hideErr(err);
    const btn = document.getElementById('mpinStep1Btn');
    btn.disabled = true; btn.textContent = 'Sending…';

    post('/app2/send-change-otp/', {
      action: 'mpin',
      new_mpin:     document.getElementById('mpin_new').value,
      confirm_mpin: document.getElementById('mpin_confirm').value
    }).then(res => {
      btn.disabled = false; btn.textContent = 'Send OTP';
      if (res.ok) {
        toStep2(
          document.getElementById('mpinStep1'),
          document.getElementById('mpinStep2'),
          document.getElementById('mpinStep1Btn'),
          document.getElementById('mpinStep2Btn'),
          document.getElementById('mpinMaskedEmail'),
          res.masked_email,
          'mpin'
        );
      } else {
        showErr(err, res.error);
      }
    }).catch(() => { btn.disabled=false; btn.textContent='Send OTP'; showErr(err,'Network error.'); });
  }

  document.getElementById('mpinStep1Btn')?.addEventListener('click', sendMpinOTP);
  document.getElementById('mpinResendBtn')?.addEventListener('click', () => {
    stopTimer('mpin');
    document.getElementById('mpinStep2').classList.add('d-none');
    document.getElementById('mpinStep1').classList.remove('d-none');
    document.getElementById('mpinStep1Btn').classList.remove('d-none');
    document.getElementById('mpinStep2Btn').classList.add('d-none');
    sendMpinOTP();
  });

  document.getElementById('mpinStep2Btn')?.addEventListener('click', () => {
    const err = document.getElementById('mpinErr2');
    hideErr(err);
    const btn = document.getElementById('mpinStep2Btn');
    btn.disabled = true; btn.textContent = 'Verifying…';

    post('/app2/verify-change-otp/', { otp: document.getElementById('mpin_otp').value })
      .then(res => {
        btn.disabled = false; btn.textContent = 'Save MPIN';
        if (res.ok) {
          bootstrap.Modal.getInstance(document.getElementById('changeMpinModal')).hide();
          showToast(res.message || 'MPIN updated!', 'success');
        } else {
          showErr(err, res.error);
        }
      }).catch(() => { btn.disabled=false; btn.textContent='Save MPIN'; showErr(err,'Network error.'); });
  });

  // ══════════════════════════
  //  TPIN
  // ══════════════════════════
  function sendTpinOTP() {
    const err = document.getElementById('tpinErr1');
    hideErr(err);
    const btn = document.getElementById('tpinStep1Btn');
    btn.disabled = true; btn.textContent = 'Sending…';

    post('/app2/send-change-otp/', {
      action: 'tpin',
      new_tpin:     document.getElementById('tpin_new').value,
      confirm_tpin: document.getElementById('tpin_confirm').value
    }).then(res => {
      btn.disabled = false; btn.textContent = 'Send OTP';
      if (res.ok) {
        toStep2(
          document.getElementById('tpinStep1'),
          document.getElementById('tpinStep2'),
          document.getElementById('tpinStep1Btn'),
          document.getElementById('tpinStep2Btn'),
          document.getElementById('tpinMaskedEmail'),
          res.masked_email,
          'tpin'
        );
      } else {
        showErr(err, res.error);
      }
    }).catch(() => { btn.disabled=false; btn.textContent='Send OTP'; showErr(err,'Network error.'); });
  }

  document.getElementById('tpinStep1Btn')?.addEventListener('click', sendTpinOTP);
  document.getElementById('tpinResendBtn')?.addEventListener('click', () => {
    stopTimer('tpin');
    document.getElementById('tpinStep2').classList.add('d-none');
    document.getElementById('tpinStep1').classList.remove('d-none');
    document.getElementById('tpinStep1Btn').classList.remove('d-none');
    document.getElementById('tpinStep2Btn').classList.add('d-none');
    sendTpinOTP();
  });

  document.getElementById('tpinStep2Btn')?.addEventListener('click', () => {
    const err = document.getElementById('tpinErr2');
    hideErr(err);
    const btn = document.getElementById('tpinStep2Btn');
    btn.disabled = true; btn.textContent = 'Verifying…';

    post('/app2/verify-change-otp/', { otp: document.getElementById('tpin_otp').value })
      .then(res => {
        btn.disabled = false; btn.textContent = 'Save TPIN';
        if (res.ok) {
          bootstrap.Modal.getInstance(document.getElementById('changeTpinModal')).hide();
          showToast(res.message || 'TPIN updated!', 'success');
        } else {
          showErr(err, res.error);
        }
      }).catch(() => { btn.disabled=false; btn.textContent='Save TPIN'; showErr(err,'Network error.'); });
  });

  // ── inline toast helper (works even without a pre-built toast element) ──
  function showToast(msg, type) {
    const div = document.createElement('div');
    div.className = `toast align-items-center text-bg-${type === 'success' ? 'success' : 'danger'} border-0 position-fixed bottom-0 end-0 m-3`;
    div.style.zIndex = 9999;
    div.setAttribute('role','alert');
    div.innerHTML = `<div class="d-flex"><div class="toast-body fw-semibold">${msg}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    document.body.appendChild(div);
    new bootstrap.Toast(div, {delay:4000}).show();
    div.addEventListener('hidden.bs.toast', () => div.remove());
  }
})();