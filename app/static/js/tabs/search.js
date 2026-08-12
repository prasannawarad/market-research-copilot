async function runSearch() {
  const query = $('#q').value.trim(), ticker = $('#q-ticker').value.trim();
  if (!query) return showErr('#q-err', 'Enter a search query.');
  $('#q-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/search', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query, ticker})});
    if (!rows.length) { $('#q-body').innerHTML = emptyState('No matches. Run the pipeline to populate embeddings.'); return; }
    $('#q-body').innerHTML = rows.map(r => {
      // Starting calibration against this app's observed live-data similarity range (~0.38-0.64), not a universal constant.
      const tier = r.similarity >= 0.55 ? ['strong','strong'] : r.similarity >= 0.40 ? ['related','material'] : ['weak','routine'];
      return `<div class="hit">
      <div class="meta">${esc(r.ticker)} &middot; similarity ${num(r.similarity,3)}
        &middot; ${tag(tier[0], tier[1])}
        ${r.sentiment ? '&middot; ' + tag(r.sentiment, esc(r.sentiment)) : ''}
        ${r.published_utc ? '&middot; ' + String(r.published_utc).slice(0,10) : ''}</div>
      <div><strong>${r.article_url ? `<a href="${esc(r.article_url)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title)}</strong></div>
      <div class="txt">${esc((r.chunk_text || '').slice(0,420))}&hellip;</div>
    </div>`;
    }).join('');
  } catch (e) { $('#q-body').innerHTML = errState(e); }
}
