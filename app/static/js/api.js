const $ = s => document.querySelector(s);
const pct = v => v == null ? '&ndash;' : (v*100).toFixed(2) + '%';
const num = (v,d=2) => v == null ? '&ndash;' : Number(v).toFixed(d);
const esc = s => (s ?? '').toString().replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
const cls = v => v == null ? 'flat' : (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
const fmtDate = v => {
  if (v == null) return '–';
  const d = new Date(v);
  return isNaN(d) ? String(v).slice(0,10) : d.toLocaleDateString('en-US', {month:'short', day:'numeric'});
};
const fmtDateTime = v => {
  if (v == null) return '–';
  const d = new Date(v);
  if (isNaN(d)) return String(v).slice(0,16).replace('T',' ');
  return d.toLocaleDateString('en-US', {month:'short', day:'numeric'}) + ', ' +
    d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
};

async function api(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || ('Request failed: ' + r.status));
  return body;
}
