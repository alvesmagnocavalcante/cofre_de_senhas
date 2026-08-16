const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

async function requestSecret(button, action) {
  const body = new FormData();
  body.append('action', action);
  const response = await fetch(button.dataset.url, {
    method: 'POST',
    headers: {'X-CSRFToken': csrfToken},
    body,
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Não foi possível acessar a senha.');
  return (await response.json()).secret;
}

document.addEventListener('click', async (event) => {
  const button = event.target.closest('.reveal, .copy');
  if (!button) return;
  button.disabled = true;
  try {
    const isCopy = button.classList.contains('copy');
    const secret = await requestSecret(button, isCopy ? 'copy' : 'reveal');
    if (isCopy) {
      await navigator.clipboard.writeText(secret);
      const previous = button.textContent;
      button.textContent = 'Copiada!';
      setTimeout(() => { button.textContent = previous; }, 1500);
    } else {
      const output = document.querySelector(`[data-secret-for="${button.dataset.id}"]`);
      const visible = output.dataset.visible === 'true';
      output.textContent = visible ? '••••••••••••' : secret;
      output.dataset.visible = visible ? 'false' : 'true';
      button.textContent = visible ? 'Mostrar' : 'Ocultar';
      if (!visible) setTimeout(() => {
        output.textContent = '••••••••••••';
        output.dataset.visible = 'false';
        button.textContent = 'Mostrar';
      }, 30000);
    }
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
});
