function tag(value, kind, attrs) {
  const attrStr = attrs && attrs.dir ? ` data-dir="${attrs.dir}"` : '';
  return `<span class="tag ${kind}"${attrStr}>${esc(value)}</span>`;
}
function trendTag(trend) {
  const kind = trend === 'up' ? 'positive' : trend === 'down' ? 'negative' : 'neutral';
  return tag(trend || 'pending', kind);
}
