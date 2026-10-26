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

  // 3. Confirm password ay dapat kapareho ng password
  const password = document.getElementById('reg-password');
  const confirm = document.getElementById('reg-confirm');
  if (password && confirm) {
    const checkMatch = () => {
      confirm.setCustomValidity(confirm.value && confirm.value !== password.value ? 'Passwords do not match' : '');
    };
    password.addEventListener('input', checkMatch);
    confirm.addEventListener('input', checkMatch);
  }

  // 4. Login/Register modal
  const modalEl = document.getElementById('authModal');
  if (modalEl) {
    const tabs = {
      login: document.getElementById('tab-login'),
      register: document.getElementById('tab-register'),
    };

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

    // Linisin ang pulang validation kapag isinara ang modal
    modalEl.addEventListener('hidden.bs.modal', () => {
      modalEl.querySelectorAll('form').forEach((form) => form.classList.remove('was-validated'));
    });
  }
});