async function loadSignals() {
  const t = $('#sig-ticker').value.trim();
  $('#sig-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/signals' + (t ? '?ticker=' + encodeURIComponent(t) : ''));
    if (!rows.length) { $('#sig-body').innerHTML = emptyState('No signals yet — run the pipeline.'); return; }
    const headerHtml = `<th>Ticker</th><th>Date</th><th>Headline</th><th class="num">Move</th>
      <th class="num">Vol z</th><th>Signal</th>`;
    const bodyRowsHtml = rows.map((r, i) => {
      const prev = rows[i - 1];
      const repeat = prev && prev.ticker === r.ticker && prev.bar_date === r.bar_date;
      return `<tr>
        <td class="sym">${esc(r.ticker)}</td>
        <td class="mono-cell">${fmtDate(r.bar_date)}</td>
        <td>${esc(r.title)}</td>
        <td class="num ${repeat ? '' : cls(r.daily_return)}">${repeat ? '' : pct(r.daily_return)}</td>
        <td class="num">${repeat ? '' : num(r.volume_zscore_20d)}</td>
        <td>${repeat ? '' : tag(r.signal_strength, esc(r.signal_strength), r.signal_strength === 'strong' ? {dir: cls(r.daily_return)} : null)}</td>
      </tr>`;
    }).join('');
    $('#sig-body').innerHTML = renderTable(headerHtml, bodyRowsHtml);
  } catch (e) { $('#sig-body').innerHTML = errState(e); }
}
