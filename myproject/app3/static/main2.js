// main2.js — handles the Deposit and Withdraw popups: validation, AJAX submit, smooth close.
document.addEventListener('DOMContentLoaded', function () {

  setupMoneyModal({
    type: 'deposit',
    modalId: 'depositModal',
    formId: 'depositForm',
    amountId: 'depositAmount',
    pinId: 'depositMpin',
    pinLabel: 'MPIN',
    errorId: 'depositError',
    submitBtnId: 'depositSubmitBtn'
  });

  setupMoneyModal({
    type: 'withdraw',
    modalId: 'withdrawModal',
    formId: 'withdrawForm',
    amountId: 'withdrawAmount',
    pinId: 'withdrawTpin',
    pinLabel: 'TPIN',
    errorId: 'withdrawError',
    submitBtnId: 'withdrawSubmitBtn'
  });

  function setupMoneyModal(cfg) {
    var modalEl = document.getElementById(cfg.modalId);
    var form = document.getElementById(cfg.formId);
    if (!modalEl || !form) return;

    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    var amountField = document.getElementById(cfg.amountId);
    var mpinField = document.getElementById(cfg.pinId);
    var mpinToggle = modalEl.querySelector('.apex-mpin-toggle, .apex-tpin-toggle');
    var errorBox = document.getElementById(cfg.errorId);
    var submitBtn = document.getElementById(cfg.submitBtnId);
    var btnLabel = submitBtn.querySelector('.apex-btn-label');
    var btnSpinner = submitBtn.querySelector('.apex-btn-spinner');
    var btnCheck = submitBtn.querySelector('.apex-btn-check');
    var maxBalance = form.dataset.balance ? parseFloat(form.dataset.balance) : null;

    mpinToggle.addEventListener('click', function () {
      var isPwd = mpinField.type === 'password';
      mpinField.type = isPwd ? 'text' : 'password';
      mpinToggle.querySelector('i').className = isPwd ? 'bi bi-eye-slash' : 'bi bi-eye';
    });

    modalEl.addEventListener('show.bs.modal', resetForm);
    modalEl.addEventListener('hidden.bs.modal', resetForm);

    function resetForm() {
      form.reset();
      clearInvalid(amountField);
      clearInvalid(mpinField);
      hideError();
      setLoading(false);
      btnCheck.classList.add('d-none');
      btnLabel.classList.remove('d-none');
      mpinField.type = 'password';
      mpinToggle.querySelector('i').className = 'bi bi-eye';
    }

    function showError(msg) {
      errorBox.textContent = msg;
      errorBox.classList.remove('d-none');
    }
    function hideError() {
      errorBox.classList.add('d-none');
      errorBox.textContent = '';
    }

    function markInvalid(field, message) {
      var wrap = field.closest('.apex-field');
      wrap.classList.add('is-invalid');
      wrap.classList.remove('shake');
      void wrap.offsetWidth;
      wrap.classList.add('shake');
      if (message) wrap.querySelector('.apex-feedback').textContent = message;
    }
    function clearInvalid(field) {
      field.closest('.apex-field').classList.remove('is-invalid', 'shake');
    }

    function setLoading(isLoading) {
      submitBtn.disabled = isLoading;
      btnLabel.classList.toggle('d-none', isLoading);
      btnSpinner.classList.toggle('d-none', !isLoading);
    }

    function validate() {
      var ok = true;
      clearInvalid(amountField);
      clearInvalid(mpinField);

      var amount = parseFloat(amountField.value);
      if (!amountField.value || isNaN(amount) || amount <= 0) {
        markInvalid(amountField, 'Enter an amount greater than zero.');
        ok = false;
      } else if (cfg.type === 'withdraw' && maxBalance !== null && amount > maxBalance) {
        markInvalid(amountField, 'Amount exceeds your available balance.');
        ok = false;
      }
      if (!mpinField.value || mpinField.value.length < 4) {
        markInvalid(mpinField, 'Enter your ' + cfg.pinLabel + ' to confirm.');
        ok = false;
      }
      return ok;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      hideError();
      if (!validate()) return;

      setLoading(true);

      fetch(form.action || window.location.href, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(function (res) {
          return res.json()
            .catch(function () {
              if (!res.ok) {
                throw new Error(cfg.type === 'withdraw'
                  ? 'Withdrawal failed. Please try again.'
                  : 'Deposit failed. Please try again.');
              }
              return { success: true };
            })
            .then(function (data) {
              return { ok: res.ok, data: data };
            });
        })
        .then(function (result) {
          if (!result.ok || result.data.success === false) {
            var serverError =
              (result.data && result.data.message) ||
              (result.data && result.data.errors && Object.values(result.data.errors)[0]) ||
              (cfg.type === 'withdraw'
                ? 'Withdrawal failed. Please check your details and try again.'
                : 'Deposit failed. Please check your details and try again.');
            throw new Error(serverError);
          }

          btnSpinner.classList.add('d-none');
          btnCheck.classList.remove('d-none');
          setTimeout(function () {
            modal.hide();
            window.location.reload();
          }, 650);
        })
        .catch(function (err) {
          setLoading(false);
          showError(err.message);
        });
    });
  }

  // ── Toasts ──
  document.querySelectorAll('.toast').forEach(el => new bootstrap.Toast(el, { delay: 4000 }).show());

  // ── Transfer page: verify receiver ──
  const recvAcc = document.getElementById('recv-acc');
  if (recvAcc) {
    let t;

   window.verifyReceiver = function () {
  const acc = recvAcc.value.trim();
  document.getElementById('recv-found').classList.remove('show');
  document.getElementById('recv-err').classList.remove('show');
  if (!acc) return;

  if (acc === window.ownAccountNumber) {
    document.getElementById('recv-err-text').textContent = 'You cannot transfer to your own account.';
    document.getElementById('recv-err').classList.add('show');
    return;
  }

  fetch(`/app3/verify-receiver/?account_number=${acc}`)
    .then(r => r.json())
    .then(d => {
      if (d.found) {
        document.getElementById('recv-name').textContent   = d.name;
        document.getElementById('recv-branch').textContent = d.branch;
        document.getElementById('recv-found').classList.add('show');
      } else {
        document.getElementById('recv-err-text').textContent = 'Account not found.';
        document.getElementById('recv-err').classList.add('show');
      }
    });
};
    recvAcc.addEventListener('input', function () {
      clearTimeout(t);
      document.getElementById('recv-found').classList.remove('show');
      document.getElementById('recv-err').classList.remove('show');
      if (this.value.length >= 8) t = setTimeout(verifyReceiver, 600);
    });
  }

  // ── Transfer page: TPIN input filter ──
  const tpinField = document.querySelector('input[name="tpin"]');
  if (tpinField) {
    tpinField.addEventListener('input', function () {
      this.value = this.value.replace(/\D/g, '').slice(0, 6);
    });
  }

  // ── Transfer page: confirm before submit ──
const transferForm = document.getElementById('transfer-form');
if (transferForm) {
  transferForm.addEventListener('submit', function (e) {
    const acc  = document.getElementById('recv-acc').value.trim();
    if (acc === window.ownAccountNumber) {
      e.preventDefault();
      document.getElementById('recv-err-text').textContent = 'You cannot transfer to your own account.';
      document.getElementById('recv-err').classList.add('show');
      return;
    }
    const amt  = document.getElementById('amt-input').value;
    const name = document.getElementById('recv-name').textContent;
    if (name && !confirm(`Confirm transfer of ₹${amt} to ${name}?`)) e.preventDefault();
  });
}

  window.setAmt = function (v) {
    const el = document.getElementById('amt-input');
    if (el) el.value = v;
  };

  // ── Transaction history: AJAX pagination ──
  const txContent = document.getElementById('tx-content');
  if (txContent) {
    function loadPage(url) {
      txContent.style.opacity = '0.5';
      txContent.style.pointerEvents = 'none';
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => r.text())
        .then(html => {
          const doc = new DOMParser().parseFromString(html, 'text/html');
          const fresh = doc.getElementById('tx-content');
          if (fresh) txContent.innerHTML = fresh.innerHTML;
          txContent.style.opacity = '1';
          txContent.style.pointerEvents = '';
          history.pushState({}, '', url);
          bindAll();
          txContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        })
        .catch(() => { window.location.href = url; });
    }

    function bindAll() {
      document.querySelectorAll('#tx-content .pg-btn[href]').forEach(a => {
        a.addEventListener('click', e => { e.preventDefault(); loadPage(a.href); });
      });
      document.querySelectorAll('.filter-tabs .ftab').forEach(a => {
        a.addEventListener('click', e => { e.preventDefault(); loadPage(a.href); });
      });
    }

    window.addEventListener('popstate', () => loadPage(location.href));
    bindAll();
  }

  // ── Statement download modal ──
  const overlay  = document.getElementById('stmtOverlay');
  const openBtn  = document.getElementById('openStmtModal');
  const closeBtn = document.getElementById('closeStmtModal');

  if (openBtn && overlay) {
    openBtn.addEventListener('click', () => overlay.classList.add('open'));
  }
  if (closeBtn && overlay) {
    closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
  }
  if (overlay) {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') overlay.classList.remove('open');
    });

    document.querySelectorAll('.stmt-period-card').forEach(card => {
      card.addEventListener('click', function () {
        this.classList.add('downloading');
        this.querySelector('.sp-arrow i').className = 'ti ti-loader';
        setTimeout(() => {
          this.classList.remove('downloading');
          this.querySelector('.sp-arrow i').className = 'ti ti-download';
          overlay.classList.remove('open');
        }, 2000);
      });
    });
  }

  // ── Smooth page transitions ──
  document.querySelectorAll('a[href]').forEach(a => {
    a.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('?')) return;
      e.preventDefault();
      document.body.style.opacity = '0';
      document.body.style.transition = 'opacity 0.3s ease';
      setTimeout(() => { window.location.href = href; }, 300);
    });
  });

});