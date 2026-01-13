/* Shared activity time-unit helpers (Days ↔ Hours)

Base unit is hours.
Display unit is hours or days.

NOTE:
- Templates must not embed conversion math.
- JS does need basic multiplication/division for live switching, but it always uses
  the per-activity `hoursPerDay` value provided by the backend.
*/

(function () {
  function toNum(v) {
    const n = Number(String(v ?? '').trim());
    return Number.isFinite(n) ? n : 0;
  }

  function normalizeUnit(u) {
    const s = String(u ?? '').trim().toLowerCase();
    if (s === 'days' || s === 'day' || s === 'd') return 'days';
    return 'hours';
  }

  function normalizeHoursPerDay(hpd, fallback) {
    const n = toNum(hpd);
    const fb = Number.isFinite(Number(fallback)) ? Number(fallback) : 8;
    return n > 0 ? n : fb;
  }

  function displayToHours(value, displayUnit, hoursPerDay) {
    const unit = normalizeUnit(displayUnit);
    const hpd = normalizeHoursPerDay(hoursPerDay, 8);
    const v = toNum(value);
    return unit === 'days' ? v * hpd : v;
  }

  function hoursToDisplay(hours, displayUnit, hoursPerDay) {
    const unit = normalizeUnit(displayUnit);
    const hpd = normalizeHoursPerDay(hoursPerDay, 8);
    const h = toNum(hours);
    return unit === 'days' ? (h / hpd) : h;
  }

  // Expose as global for pages.
  window.ActivityUnits = {
    toNum,
    normalizeUnit,
    normalizeHoursPerDay,
    displayToHours,
    hoursToDisplay
  };
})();
