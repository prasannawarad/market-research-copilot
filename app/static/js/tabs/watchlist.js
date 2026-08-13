let sparkCharts = [];

async function loadWatchlist() {
  $('#wl-body').innerHTML = emptyState('Loading&hellip;');
  try {
    const rows = await api('/api/watchlist');
    if (!rows.length) {
      $('#wl-body').innerHTML = emptyState('No tickers yet. Add one above, then run the Spark pipeline.');
      $('#s-metrics-ctx').textContent = '';
      return;
    }
    const scoredRows = rows.filter(r => r.trend != null);
    const pendingRows = rows.filter(r => r.trend == null);

    const headerHtml = `<th>Symbol</th><th>Trend</th><th class="num">Close</th><th class="num">Day</th>
      <th class="num">Vol 20d</th><th class="num">Drawdown</th><th class="num">As of</th><th></th>`;
    const bodyRowsHtml = scoredRows.map(r => `<tr>
        <td class="sym" onclick="showDetail('${esc(r.symbol)}')">${esc(r.symbol)}</td>
        <td><div class="spark-cell"><canvas class="spark-canvas" id="spark-${esc(r.symbol)}" width="72" height="22"></canvas></div></td>
        <td class="num">${r.close != null ? num(r.close) : (r.latest_price != null ? num(r.latest_price) : '&ndash;')}</td>
        <td class="num ${cls(r.daily_return)}">${pct(r.daily_return)}</td>
        <td class="num">${pct(r.volatility_20d)}</td>
        <td class="num ${cls(r.drawdown_from_high)}">${pct(r.drawdown_from_high)}</td>
        <td class="num dim">${r.bar_date ? fmtDate(r.bar_date) : '&ndash;'}</td>
        <td class="num"><button class="x" onclick="removeSymbol('${esc(r.symbol)}')">Remove</button></td>
      </tr>`).join('');

    let html = scoredRows.length
      ? renderTable(headerHtml, bodyRowsHtml, 'compact')
      : emptyState('No scored tickers yet — run the Spark pipeline.');

    if (pendingRows.length) {
      html += `<div class="section-head sub">
          <h2>Awaiting pipeline</h2>
          <span class="hint">${pendingRows.length} ticker${pendingRows.length === 1 ? '' : 's'} not yet scored</span>
        </div>
        <div class="pending-list">${pendingRows.map(r => `<span class="pending-chip">${esc(r.symbol)}
          <button class="x sm" onclick="removeSymbol('${esc(r.symbol)}')" aria-label="Remove ${esc(r.symbol)}">&times;</button></span>`).join('')}</div>`;
    }

    $('#wl-body').innerHTML = html;
    $('#s-metrics-ctx').textContent = `${scoredRows.length} of ${rows.length} tickers scored`;
    renderSparklines(scoredRows);
  } catch (e) { $('#wl-body').innerHTML = errState(e); $('#s-metrics-ctx').textContent = ''; }
}

async function renderSparklines(rows) {
  sparkCharts.forEach(c => c.destroy());
  sparkCharts = [];
  const symbols = rows.map(r => r.symbol);
  const settled = await Promise.allSettled(symbols.map(sym => api('/api/metrics/' + sym + '?days=20')));
  const chartAvailable = !!window.Chart;
  settled.forEach((result, i) => {
    const canvasEl = document.getElementById('spark-' + symbols[i]);
    if (!canvasEl) return;
    const failed = result.status === 'rejected';
    const closesDesc = !failed ? result.value.filter(r => r.close != null).map(r => r.close) : [];
    const hasEnoughData = !failed && closesDesc.length >= 2;
    if (!chartAvailable || !hasEnoughData) {
      const titleAttr = (chartAvailable && failed) ? ' title="Failed to load price history"' : '';
      canvasEl.outerHTML = `<span class="spark-empty"${titleAttr}>Insufficient history</span>`;
      return;
    }
    const closes = closesDesc.slice().reverse();
    const clsName = cls(closes[closes.length - 1] - closes[0]);
    const color = getComputedStyle(document.documentElement).getPropertyValue('--' + clsName).trim();
    const chart = new Chart(canvasEl, {
      type: 'line',
      data: {
        labels: closes.map((_, idx) => idx),
        datasets: [{
          data: closes,
          borderColor: color,
          borderWidth: 1.5,
          tension: 0,
          fill: false,
          pointRadius: 0
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        scales: { x: { display: false }, y: { display: false } },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        elements: { point: { radius: 0 } }
      }
    });
    sparkCharts.push(chart);
  });
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
        <td class="mono-cell">${fmtDate(r.bar_date)}</td>
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
