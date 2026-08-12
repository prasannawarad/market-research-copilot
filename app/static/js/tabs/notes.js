async function loadNotes() {
  $('#notes-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/notes');
    if (!rows.length) { $('#notes-body').innerHTML = emptyState('No notes yet.'); return; }
    $('#notes-body').innerHTML = rows.map(r => `<div class="note${r.author === 'agent' ? ' agent' : ''}">
      <div class="meta"><strong>${esc(r.ticker)}</strong> &middot;
        ${tag(r.author, esc(r.author))} &middot;
        ${String(r.created_at).slice(0,16).replace('T',' ')}
        &middot; <a href="#" onclick="delNote(${r.note_id});return false" style="color:var(--down)">delete</a></div>
      <div>${esc(r.note_text)}</div></div>`).join('');
  } catch (e) { $('#notes-body').innerHTML = errState(e); }
}

async function saveNote() {
  const ticker = $('#note-ticker').value.trim(), note_text = $('#note-text').value.trim();
  if (!ticker) return showErr('#note-err', 'Pick a ticker for this note.');
  if (!note_text) return showErr('#note-err', 'Write something before saving.');
  try {
    await api('/api/notes', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ticker, note_text})});
    $('#note-text').value = '';
    loadNotes();
  } catch (e) { showErr('#note-err', e.message); }
}

async function delNote(id) {
  if (!confirm('Delete this note?')) return;
  try { await api('/api/notes/' + id, {method:'DELETE'}); loadNotes(); }
  catch (e) { showErr('#note-err', e.message); }
}
