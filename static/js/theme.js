(function () {
  const storageKey = 'carmel-cofre-theme';
  const savedTheme = localStorage.getItem(storageKey);
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.theme = savedTheme || systemTheme;

  function updateControls() {
    const isDark = document.documentElement.dataset.theme === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.setAttribute('aria-label', isDark ? 'Ativar modo claro' : 'Ativar modo escuro');
      button.querySelector('[data-theme-label]').textContent = isDark ? 'Modo claro' : 'Modo escuro';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    updateControls();
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.addEventListener('click', () => {
        const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = nextTheme;
        localStorage.setItem(storageKey, nextTheme);
        updateControls();
      });
    });
  });
})();
