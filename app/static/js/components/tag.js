function tag(value, kind) {
  return `<span class="tag ${kind}">${esc(value)}</span>`;
}
function trendTag(trend) {
  const kind = trend === 'up' ? 'positive' : trend === 'down' ? 'negative' : 'neutral';
  return tag(trend || 'n/a', kind);
}
