/* InfraCore - Project picker (Daily Execution)
   - Fast client-side search
   - Quick type filters
*/

(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  const grid = qs('#projectGrid');
  if (!grid) return;

  const search = qs('#projectSearch');
  const chips = qsa('.chip[data-filter]');
  const visibleCount = qs('#visibleCount');
  const noResults = qs('#noResults');

  const cards = qsa('.proj-card', grid);
  let activeFilter = 'all';

  function norm(v) {
    return String(v || '').toLowerCase().trim();
  }

  function matchesType(card, filter) {
    if (filter === 'all') return true;
    const type = norm(card.dataset.type);
    if (!type) return false;
    if (filter === 'road') return type === 'road' || type.includes('road');
    if (filter === 'building') return type === 'building' || type.includes('building');
    if (filter === 'bridge') return type === 'bridge' || type.includes('bridge');
    return type.includes(filter);
  }

  function apply() {
    const q = norm(search?.value);
    let shown = 0;

    for (const card of cards) {
      const hay = `${card.dataset.name || ''} ${card.dataset.location || ''} ${card.dataset.type || ''}`;
      const okSearch = !q || norm(hay).includes(q);
      const okType = matchesType(card, activeFilter);
      const show = okSearch && okType;
      card.style.display = show ? '' : 'none';
      if (show) shown++;
    }

    if (visibleCount) visibleCount.textContent = String(shown);
    if (noResults) noResults.style.display = shown === 0 ? '' : 'none';
  }

  function setFilter(value) {
    activeFilter = value;
    chips.forEach(c => c.classList.toggle('active', c.dataset.filter === value));
    apply();
  }

  if (search) {
    search.addEventListener('input', apply);
    search.addEventListener('keydown', (e) => {
      // quick clear
      if (e.key === 'Escape') {
        search.value = '';
        apply();
      }
    });
  }

  chips.forEach(c => c.addEventListener('click', () => setFilter(c.dataset.filter || 'all')));

  // initial
  apply();
})();
