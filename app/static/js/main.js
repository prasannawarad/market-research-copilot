document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  t.classList.add('on');
  ['watchlist','search','signals','notes','reports'].forEach(v =>
    $('#v-' + v).classList.toggle('hide', v !== t.dataset.view));
  if (t.dataset.view === 'signals') loadSignals();
  if (t.dataset.view === 'notes') loadNotes();
  if (t.dataset.view === 'reports') loadReports();
});

async function loadStats() {
  try {
    const s = await api('/api/stats');
    $('#s-bars').textContent = s.bars ?? 0;
    $('#s-articles').textContent = s.articles ?? 0;
    $('#s-chunks').textContent = s.chunks ?? 0;
    $('#s-signals').textContent = s.signals ?? 0;
    $('#s-latest').textContent = s.latest_bar ? fmtDate(s.latest_bar) : '—';
  } catch (e) { console.error(e); }
}

$('#new-symbol').addEventListener('keydown', e => { if (e.key === 'Enter') addSymbol(); });
$('#q').addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });

loadStats();
loadWatchlist();
