async function loadWatchlist() {
  try {
    const rows = await api('/api/watchlist');
    if (!rows.length) {
      $('#wl-body').innerHTML = emptyState('No tickers yet. Add one above, then run the Spark pipeline.');
      return;
    }
    const headerHtml = `<th>Symbol</th><th>Trend</th><th class="num">Close</th><th class="num">Day</th>
      <th class="num">Vol 20d</th><th class="num">Drawdown</th><th class="num">As of</th><th></th>`;
    const bodyRowsHtml = rows.map(r => `<tr>
        <td class="sym" onclick="showDetail('${esc(r.symbol)}')">${esc(r.symbol)}</td>
        <td>${trendTag(r.trend)}</td>
        <td class="num">${r.close != null ? num(r.close) : (r.latest_price != null ? num(r.latest_price) : '&ndash;')}</td>
        <td class="num ${cls(r.daily_return)}">${pct(r.daily_return)}</td>
        <td class="num">${pct(r.volatility_20d)}</td>
        <td class="num ${cls(r.drawdown_from_high)}">${pct(r.drawdown_from_high)}</td>
        <td class="num" style="color:var(--muted);font-size:12px">${r.bar_date ? String(r.bar_date).slice(0,10) : '&ndash;'}</td>
        <td class="num"><button class="x" onclick="removeSymbol('${esc(r.symbol)}')">Remove</button></td>
      </tr>`).join('');
    $('#wl-body').innerHTML = renderTable(headerHtml, bodyRowsHtml);
  } catch (e) { $('#wl-body').innerHTML = errState(e); }
}

async function addSymbol() {
  const symbol = $('#new-symbol').value.trim().toUpperCase();
  if (!symbol) return showErr('#wl-err', 'Enter a ticker symbol.');
  try {
    await api('/api/watchlist', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({symbol})});
    $('#new-symbol').value = '';
    loadWatchlist();
  } catch (e) { showErr('#wl-err', e.message); }
}

async function removeSymbol(symbol) {
  if (!confirm('Remove ' + symbol + ' from the watchlist?')) return;
  try { await api('/api/watchlist/' + symbol, {method:'DELETE'}); loadWatchlist(); }
  catch (e) { showErr('#wl-err', e.message); }
}

async function showDetail(ticker) {
  $('#detail-panel').classList.remove('hide');
  $('#detail-title').textContent = ticker + ' — last 20 sessions';
  $('#detail-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/metrics/' + ticker + '?days=20');
    if (!rows.length) { $('#detail-body').innerHTML = emptyState('No metrics yet — run the pipeline.'); return; }
    const headerHtml = `<th>Date</th><th class="num">Close</th><th class="num">Return</th><th class="num">MA5</th>
      <th class="num">MA20</th><th class="num">Vol 20d</th><th class="num">Vol z</th><th>Trend</th>`;
    const bodyRowsHtml = rows.map(r => `<tr>
        <td>${String(r.bar_date).slice(0,10)}</td>
        <td class="num">${num(r.close)}</td>
        <td class="num ${cls(r.daily_return)}">${pct(r.daily_return)}</td>
        <td class="num">${num(r.ma_5)}</td><td class="num">${num(r.ma_20)}</td>
        <td class="num">${pct(r.volatility_20d)}</td>
        <td class="num">${num(r.volume_zscore_20d)}</td>
        <td>${trendTag(r.trend)}</td>
      </tr>`).join('');
    $('#detail-body').innerHTML = renderTable(headerHtml, bodyRowsHtml);
  } catch (e) { $('#detail-body').innerHTML = errState(e); }
}
