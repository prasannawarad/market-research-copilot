async function loadReports() {
  try {
    const rows = await api('/api/reports');
    if (!rows.length) { $('#rep-body').innerHTML = emptyState('No agent analyses saved yet. Ask the agent a question and have it call save_analysis_report.'); return; }
    $('#rep-body').innerHTML = rows.map(r => `<div class="note">
      <div class="meta"><strong>${esc(r.ticker)}</strong> &middot; ${esc(r.model_name || 'agent')} &middot;
        ${String(r.created_at).slice(0,16).replace('T',' ')}</div>
      <div style="margin-bottom:6px"><strong>${esc(r.question)}</strong></div>
      <div style="color:var(--soft)">${esc(r.answer)}</div>
      ${Array.isArray(r.citations) && r.citations.length
        ? '<div class="meta" style="margin-top:6px">' + r.citations.map(c => esc(String(c))).join(' &middot; ') + '</div>' : ''}
    </div>`).join('');
  } catch (e) { $('#rep-body').innerHTML = errState(e); }
}
