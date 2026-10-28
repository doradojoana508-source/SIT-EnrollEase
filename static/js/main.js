document.addEventListener('DOMContentLoaded', () => {

  // 1. Client-side validation para sa lahat ng form na may class na "needs-validation"
  document.querySelectorAll('form.needs-validation').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

  // 2. Show/hide password
  document.querySelectorAll('[data-toggle-password]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.togglePassword);
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      button.querySelector('i').className = showing ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  });

  // 3. Confirm password ay dapat kapareho ng password (Register sa modal)
  const password = document.getElementById('reg-password');
  const confirm = document.getElementById('reg-confirm');
  if (password && confirm) {
    const checkMatch = () => {
      confirm.setCustomValidity(confirm.value && confirm.value !== password.value ? 'Passwords do not match' : '');
    };
    password.addEventListener('input', checkMatch);
    confirm.addEventListener('input', checkMatch);
  }

  // 4. Pareho rin para sa kahit anong field na may data-match="id-ng-password"
  document.querySelectorAll('input[data-match]').forEach((input) => {
    const target = document.getElementById(input.dataset.match);
    const check = () => {
      input.setCustomValidity(input.value && input.value !== target.value ? 'Passwords do not match' : '');
    };
    input.addEventListener('input', check);
    target.addEventListener('input', check);
  });

  // 5. Login/Register/Forgot modal
  const modalEl = document.getElementById('authModal');
  if (modalEl) {
    const tabs = {
      login: document.getElementById('tab-login'),
      register: document.getElementById('tab-register'),
    };
    const loginBlock = document.getElementById('login-block');
    const forgotBlock = document.getElementById('forgot-block');

    const showForgot = (on) => {
      loginBlock.classList.toggle('d-none', on);
      forgotBlock.classList.toggle('d-none', !on);
    };
    document.getElementById('show-forgot').addEventListener('click', () => showForgot(true));
    document.getElementById('back-to-login').addEventListener('click', () => showForgot(false));

    // Buksan sa tamang tab ayon sa pinindot na button (data-auth-tab)
    modalEl.addEventListener('show.bs.modal', (event) => {
      const wanted = event.relatedTarget ? event.relatedTarget.dataset.authTab : null;
      if (wanted && tabs[wanted]) {
        bootstrap.Tab.getOrCreateInstance(tabs[wanted]).show();
      }
    });

    // Palitan ang teksto sa kaliwang panel kapag nagpalit ng tab
    modalEl.querySelectorAll('[data-bs-toggle="pill"]').forEach((button) => {
      button.addEventListener('shown.bs.tab', () => {
        modalEl.querySelectorAll('[data-brand]').forEach((el) => {
          el.classList.toggle('d-none', el.dataset.brand !== button.dataset.authName);
        });
      });
    });

    // Linisin ang pulang validation at ibalik sa login kapag isinara ang modal
    modalEl.addEventListener('hidden.bs.modal', () => {
      modalEl.querySelectorAll('form').forEach((form) => form.classList.remove('was-validated'));
      showForgot(false);
    });

    // Kusang bumukas kapag may error, o galing sa redirect na may ?auth=login
    const autoOpen = modalEl.dataset.authOpen;
    const startTab = autoOpen === 'forgot' ? 'login' : autoOpen;
    if (autoOpen && tabs[startTab]) {
      bootstrap.Tab.getOrCreateInstance(tabs[startTab]).show();
      if (autoOpen === 'forgot') showForgot(true);
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
      if (window.location.search) history.replaceState({}, '', window.location.pathname);
    }
  }
});

// ===== Toast notifications (kusang nawawala) =====
(function () {
  const ICONS = { success: 'bi-check-circle-fill', danger: 'bi-x-octagon-fill',
                  warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  const TIMES = { success: 5000, info: 5000, warning: 7000, danger: 8000 };

  function dismiss(toast) {
    if (toast.classList.contains('leaving')) return;
    toast.classList.add('leaving');
    setTimeout(() => toast.remove(), 250);
  }

  function wire(toast) {
    toast.querySelector('.sit-toast-close').addEventListener('click', () => dismiss(toast));
    // Kapag naubos na ang progress bar, mawawala na ang toast
    toast.querySelector('.sit-toast-bar').addEventListener('animationend', () => dismiss(toast));
  }

  // Gamitin sa JavaScript: showToast('Saved!', 'success')
  window.showToast = function (message, category = 'info') {
    const cat = ICONS[category] ? category : 'info';
    let stack = document.getElementById('toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'toast-stack';
      stack.className = 'toast-stack';
      document.body.appendChild(stack);
    }
    const toast = document.createElement('div');
    toast.className = `sit-toast sit-toast-${cat}`;
    toast.setAttribute('role', 'alert');
    toast.style.setProperty('--toast-ms', TIMES[cat] + 'ms');
    toast.innerHTML = `<i class="bi ${ICONS[cat]} sit-toast-icon"></i>
      <div class="sit-toast-body"></div>
      <button type="button" class="sit-toast-close" aria-label="Close"><i class="bi bi-x-lg"></i></button>
      <span class="sit-toast-bar"></span>`;
    toast.querySelector('.sit-toast-body').textContent = message;   // textContent: ligtas sa XSS
    stack.appendChild(toast);
    wire(toast);
  };

  document.querySelectorAll('.sit-toast').forEach(wire);
})();