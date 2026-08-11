function showErr(id, msg) {
  const el = $(id); el.textContent = msg; el.classList.remove('hide');
  setTimeout(() => el.classList.add('hide'), 6000);
}
function emptyState(msg) { return `<div class="empty">${msg}</div>`; }
function errState(err) { return `<div class="err">${esc(err.message)}</div>`; }
