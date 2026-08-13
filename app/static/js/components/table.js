function renderTable(headerHtml, bodyRowsHtml, extraClass) {
  const cls = extraClass ? ' class="' + extraClass + '"' : '';
  return '<div class="table-scroll"><table' + cls + '><thead><tr>' + headerHtml + '</tr></thead><tbody>'
    + bodyRowsHtml + '</tbody></table></div>';
}
