/* Activity Planning: per-activity display unit switching (hours ↔ days)

This script keeps a hidden base-hours field in sync so:
- switching units never loses data
- backend always receives hours (system standard)
*/

(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  if (!window.ActivityUnits) {
    console.warn('ActivityUnits helper missing; include /static/js/activity_units.js');
  }

  function setText(el, text) {
    if (el) el.textContent = String(text);
  }

  function setTitle(el, title) {
    if (el) el.title = String(title || '');
  }

  function recomputeRow(row) {
    const unitSel = qs('select.activity-display-unit', row);
    const hpdInput = qs('input.activity-hours-per-day', row);
    const displayInput = qs('input.activity-planned-display', row);
    const hoursHidden = qs('input.activity-planned-hours', row);
    const unitLabel = qs('.activity-unit-label', row);
    const helper = qs('.activity-hpd-helper', row);

    const displayUnit = (unitSel && unitSel.value) || 'hours';
    const hoursPerDay = (hpdInput && hpdInput.value) || 8;

    // Update labels
    setText(unitLabel, displayUnit === 'days' ? 'days' : 'hrs');
    setText(helper, `1 day = ${window.ActivityUnits ? window.ActivityUnits.normalizeHoursPerDay(hoursPerDay, 8) : hoursPerDay} working hours`);

    // If hidden is empty (legacy), derive from display.
    const baseHours = window.ActivityUnits
      ? window.ActivityUnits.displayToHours(displayInput?.value, displayUnit, hoursPerDay)
      : Number(displayInput?.value || 0);

    if (hoursHidden) hoursHidden.value = String(baseHours);

    // Keep display normalized based on base hours
    const shown = window.ActivityUnits
      ? window.ActivityUnits.hoursToDisplay(baseHours, displayUnit, hoursPerDay)
      : baseHours;

    if (displayInput) {
      displayInput.value = (Number.isFinite(shown) ? shown : 0).toFixed(3);
    }

    // Validation hints
    if (displayInput) {
      const v = window.ActivityUnits ? window.ActivityUnits.toNum(displayInput.value) : Number(displayInput.value || 0);
      const invalid = v <= 0;
      displayInput.classList.toggle('invalid', invalid);
      setTitle(displayInput, invalid ? 'Planned quantity must be > 0' : '');
    }
  }

  function wire() {
    qsa('tr[data-activity-id]').forEach(row => {
      const unitSel = qs('select.activity-display-unit', row);
      const hpdInput = qs('input.activity-hours-per-day', row);
      const displayInput = qs('input.activity-planned-display', row);

      const handler = () => recomputeRow(row);

      if (unitSel) unitSel.addEventListener('change', handler);
      if (hpdInput) hpdInput.addEventListener('input', handler);
      if (displayInput) displayInput.addEventListener('input', handler);

      // initial
      handler();
    });
  }

  document.addEventListener('DOMContentLoaded', wire);
})();
