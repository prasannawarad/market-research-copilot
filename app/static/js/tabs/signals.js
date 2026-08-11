async function loadSignals() {
  const t = $('#sig-ticker').value.trim();
  $('#sig-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/signals' + (t ? '?ticker=' + encodeURIComponent(t) : ''));
    if (!rows.length) { $('#sig-body').innerHTML = emptyState('No signals yet — run the pipeline.'); return; }
    const headerHtml = `<th>Ticker</th><th>Date</th><th>Headline</th><th class="num">Move</th>
      <th class="num">Vol z</th><th>Signal</th>`;
    const bodyRowsHtml = rows.map(r => `<tr>
        <td class="sym">${esc(r.ticker)}</td>
        <td style="font-family:var(--mono);font-size:12px">${String(r.bar_date).slice(0,10)}</td>
        <td>${esc(r.title)}</td>
        <td class="num ${cls(r.daily_return)}">${pct(r.daily_return)}</td>
        <td class="num">${num(r.volume_zscore_20d)}</td>
        <td>${tag(r.signal_strength, esc(r.signal_strength))}</td>
      </tr>`).join('');
    $('#sig-body').innerHTML = renderTable(headerHtml, bodyRowsHtml);
  } catch (e) { $('#sig-body').innerHTML = errState(e); }
}
