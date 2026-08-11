const $ = s => document.querySelector(s);
const pct = v => v == null ? '&ndash;' : (v*100).toFixed(2) + '%';
const num = (v,d=2) => v == null ? '&ndash;' : Number(v).toFixed(d);
const esc = s => (s ?? '').toString().replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
const cls = v => v == null ? 'flat' : (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');

async function api(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || ('Request failed: ' + r.status));
  return body;
}
