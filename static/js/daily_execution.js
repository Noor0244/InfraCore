/* InfraCore - Daily Work Execution (DPR)
   - Header gating
   - Planned vs executed validation
   - Material planned consumption auto-calc
   - Dynamic rows (labour/machinery/qc/delays)
*/

(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function toNum(v) {
    const n = Number(String(v ?? "").trim());
    return Number.isFinite(n) ? n : 0;
  }

  function setInvalid(el, isInvalid, msg) {
    if (!el) return;
    el.classList.toggle('invalid', !!isInvalid);
    if (msg) el.title = msg;
  }

  const form = qs('#dprForm');
  if (!form) return;

  // Activity → material map (rendered as JSON in template)
  let AM_MAP = {};
  try {
    const el = qs('#amMapJson');
    AM_MAP = el ? JSON.parse(el.textContent || '{}') : {};
  } catch (e) {
    AM_MAP = {};
  }

  const headerRequired = [
    '#report_date',
    '#weather',
    '#shift',
    '#work_chainage_from',
    '#work_chainage_to',
    '#supervisor_name'
  ];

  const gatedSection = qs('#dprGated');

  function headerComplete() {
    let ok = true;
    for (const sel of headerRequired) {
      const el = qs(sel);
      const v = (el && el.value || '').trim();
      const missing = !v;
      setInvalid(el, missing, missing ? 'Required' : '');
      if (missing) ok = false;
    }
    return ok;
  }

  function setGatedEnabled(enabled) {
    if (!gatedSection) return;
    qsa('input, select, textarea, button', gatedSection).forEach(el => {
      if (el.dataset.alwaysEnabled === '1') return;
      el.disabled = !enabled;
    });
    gatedSection.classList.toggle('disabled-section', !enabled);
  }

  function recomputeActivitiesAndMaterials() {
    // Activities
    const activityRows = qsa('tr[data-activity-id]');

    const executedByActivity = {};

    activityRows.forEach(row => {
      const activityId = row.dataset.activityId;
      const planned = toNum(row.dataset.planned);
      const cumOther = toNum(row.dataset.cumOther);
      const plannedEnd = row.dataset.plannedEnd || '';

      // Time (base unit = hours)
      const plannedHours = toNum(row.dataset.plannedHours);
      const cumOtherHours = toNum(row.dataset.cumOtherHours);
      const hoursPerDay = window.ActivityUnits
        ? window.ActivityUnits.normalizeHoursPerDay(row.dataset.hoursPerDay, 8)
        : 8;

      const executedInput = qs('input.activity-executed', row);
      const remarksInput = qs('input.activity-remarks, textarea.activity-remarks', row);

      const timeUnitSel = qs('select.activity-time-unit', row);
      const timeExecutedInput = qs('input.activity-executed-time', row);
      const timeExecutedHoursHidden = qs('input.activity-executed-hours', row);

      const executedToday = toNum(executedInput?.value);
      executedByActivity[activityId] = executedToday;

      const remaining = Math.max(planned - cumOther, 0);
      const invalid = executedToday < 0 || executedToday > remaining + 1e-9;
      setInvalid(executedInput, invalid, invalid ? `Max allowed today: ${remaining}` : '');

      const cumulative = Math.min(cumOther + executedToday, planned);
      const balance = Math.max(planned - cumulative, 0);

      const cumulativeCell = qs('.cell-cumulative', row);
      const balanceCell = qs('.cell-balance', row);
      if (cumulativeCell) cumulativeCell.textContent = cumulative.toFixed(3);
      if (balanceCell) balanceCell.textContent = balance.toFixed(3);

      // Status
      let status = 'Not Started';
      if (cumulative >= planned && planned > 0) status = 'Completed';
      else if (cumulative > 0) status = 'In Progress';

      // Delay rule: if report date beyond planned end and not complete => Delayed
      const reportDate = (qs('#report_date')?.value || '').trim();
      if (reportDate && plannedEnd && reportDate > plannedEnd && cumulative < planned) {
        status = 'Delayed';
      }

      const statusCell = qs('.cell-status', row);
      if (statusCell) statusCell.textContent = status;

      // Remarks required: executed == 0 OR delayed
      const remarksRequired = (executedToday === 0) || (status === 'Delayed');
      if (remarksInput) {
        remarksInput.required = remarksRequired;
        setInvalid(remarksInput, remarksRequired && !(remarksInput.value || '').trim(), remarksRequired ? 'Remarks required' : '');
      }

      // ---- Time tracking ----
      // Note: time tracking is optional per activity.
      // If plannedHours is 0, we still sync hidden hours, but we don't hard-fail.
      if (timeUnitSel && timeExecutedInput && window.ActivityUnits) {
        const unit = window.ActivityUnits.normalizeUnit(timeUnitSel.value);
        const execDisplay = window.ActivityUnits.toNum(timeExecutedInput.value);
        let execHours = window.ActivityUnits.displayToHours(execDisplay, unit, hoursPerDay);
        if (execHours < 0) execHours = 0;

        const remainingHours = Math.max(plannedHours - cumOtherHours, 0);
        const invalidTime = (plannedHours > 0) && (execHours > remainingHours + 1e-9);
        if (invalidTime) {
          execHours = remainingHours;
          timeExecutedInput.value = window.ActivityUnits.hoursToDisplay(execHours, unit, hoursPerDay).toFixed(3);
        }

        if (timeExecutedHoursHidden) timeExecutedHoursHidden.value = String(execHours);
        setInvalid(
          timeExecutedInput,
          invalidTime,
          invalidTime ? `Max allowed today: ${window.ActivityUnits.hoursToDisplay(remainingHours, unit, hoursPerDay).toFixed(3)} ${unit}` : ''
        );

        const cumAfterHours = (plannedHours > 0)
          ? Math.min(cumOtherHours + execHours, plannedHours)
          : (cumOtherHours + execHours);
        const balanceHours = (plannedHours > 0)
          ? Math.max(plannedHours - cumAfterHours, 0)
          : 0;

        const cumCell = qs('.cell-time-cumulative', row);
        const balCell = qs('.cell-time-balance', row);
        if (cumCell) cumCell.textContent = window.ActivityUnits.hoursToDisplay(cumAfterHours, unit, hoursPerDay).toFixed(3);
        if (balCell) balCell.textContent = window.ActivityUnits.hoursToDisplay(balanceHours, unit, hoursPerDay).toFixed(3);
      }
    });

    // Materials planned consumption (auto-linked)
    const map = AM_MAP || {};
    const matPlanned = {};

    Object.keys(map).forEach(activityId => {
      const executed = toNum(executedByActivity[activityId]);
      if (!executed || executed <= 0) return;
      (map[activityId] || []).forEach(m => {
        const materialId = String(m.material_id);
        const rate = toNum(m.rate);
        matPlanned[materialId] = (matPlanned[materialId] || 0) + executed * rate;
      });
    });

    qsa('tr[data-material-id]').forEach(row => {
      const materialId = row.dataset.materialId;
      const plannedToday = toNum(matPlanned[materialId]);
      const plannedCell = qs('.cell-mat-planned', row);
      if (plannedCell) plannedCell.textContent = plannedToday ? plannedToday.toFixed(3) : '0.000';

      const plannedHidden = qs('input.mat-planned-hidden', row);
      if (plannedHidden) plannedHidden.value = plannedToday ? String(plannedToday) : '0';

      // Auto-hide if irrelevant and no input
      const issued = toNum(qs('input.mat-issued', row)?.value);
      const consumed = toNum(qs('input.mat-consumed', row)?.value);
      const shouldShow = plannedToday > 0 || issued > 0 || consumed > 0;
      row.style.display = shouldShow ? '' : 'none';

      const stock = toNum(row.dataset.stock);
      const consumedInput = qs('input.mat-consumed', row);
      const invalid = consumed > stock + 1e-9 || consumed < 0;
      setInvalid(consumedInput, invalid, invalid ? `Insufficient stock (available ${stock})` : '');
    });

    // Summary
    const totalQty = Object.values(executedByActivity).reduce((a, b) => a + toNum(b), 0);
    const totalMat = Object.values(matPlanned).reduce((a, b) => a + toNum(b), 0);

    const totalQtyEl = qs('#summary_total_qty');
    if (totalQtyEl) totalQtyEl.textContent = totalQty.toFixed(3);

    const totalMatEl = qs('#summary_total_mat');
    if (totalMatEl) totalMatEl.textContent = totalMat.toFixed(3);
  }

  // Dynamic rows helpers
  function addRow(tableId, rowHtml) {
    const tbody = qs(`#${tableId} tbody`);
    if (!tbody) return;
    const tr = document.createElement('tr');
    tr.innerHTML = rowHtml;
    tbody.appendChild(tr);
  }

  function wireDynamicTables() {
    // Labour
    const addLabourBtn = qs('#addLabourRow');
    if (addLabourBtn) {
      addLabourBtn.addEventListener('click', () => {
        addRow('labourTable', `
          <td>
            <select class="lab-category">
              <option>Skilled</option>
              <option>Unskilled</option>
              <option>Operator</option>
              <option>Supervisor</option>
            </select>
          </td>
          <td><input type="number" min="0" class="lab-workers" value="0"></td>
          <td><input type="number" min="0" step="0.5" class="lab-hours" value="0"></td>
          <td><input type="number" min="0" step="0.5" class="lab-ot" value="0"></td>
          <td><input type="text" class="lab-agency" placeholder="Agency/Contractor"></td>
          <td><button type="button" class="btn-danger btn-sm remove-row">Remove</button></td>
        `);
      });
    }

    // Machinery
    const addMachBtn = qs('#addMachRow');
    if (addMachBtn) {
      addMachBtn.addEventListener('click', () => {
        addRow('machineryTable', `
          <td><input type="text" class="mach-name" placeholder="Excavator / Roller" ></td>
          <td><input type="number" min="0" step="0.5" class="mach-hours" value="0"></td>
          <td><input type="number" min="0" step="0.5" class="mach-idle" value="0"></td>
          <td><input type="number" min="0" step="0.1" class="mach-fuel" value="0"></td>
          <td>
            <select class="mach-breakdown">
              <option value="No">No</option>
              <option value="Yes">Yes</option>
            </select>
          </td>
          <td><input type="text" class="mach-break-remarks" placeholder="Required if breakdown"></td>
          <td><button type="button" class="btn-danger btn-sm remove-row">Remove</button></td>
        `);
      });
    }

    // QC
    const addQcBtn = qs('#addQcRow');
    if (addQcBtn) {
      addQcBtn.addEventListener('click', () => {
        addRow('qcTable', `
          <td>
            <select class="qc-type">
              <option>Compaction</option>
              <option>Gradation</option>
              <option>Cube</option>
              <option>Slump</option>
              <option>Bitumen Content</option>
              <option>Other</option>
            </select>
          </td>
          <td><input type="text" class="qc-location" placeholder="Chainage/Location"></td>
          <td><input type="text" class="qc-value" placeholder="Value"></td>
          <td>
            <select class="qc-result">
              <option value="Pass">Pass</option>
              <option value="Fail">Fail</option>
            </select>
          </td>
          <td><input type="text" class="qc-engineer" placeholder="Engineer"></td>
          <td><button type="button" class="btn-danger btn-sm remove-row">Remove</button></td>
        `);
      });
    }

    // Delays
    const addDelayBtn = qs('#addDelayRow');
    if (addDelayBtn) {
      addDelayBtn.addEventListener('click', () => {
        addRow('delayTable', `
          <td>
            <select class="delay-type">
              <option>Rain</option>
              <option>Utility</option>
              <option>Material</option>
              <option>Labour</option>
              <option>Land</option>
            </select>
          </td>
          <td><input type="time" class="delay-start"></td>
          <td><input type="time" class="delay-end"></td>
          <td><input type="text" class="delay-party" placeholder="Responsible"></td>
          <td><input type="number" min="0" step="0.25" class="delay-impact-hours" value="0"></td>
          <td><input type="number" min="0" step="0.01" class="delay-impact-qty" value="0"></td>
          <td><input type="text" class="delay-remarks" placeholder="Remarks"></td>
          <td><button type="button" class="btn-danger btn-sm remove-row">Remove</button></td>
        `);
      });
    }

    // Remove row handler (delegated)
    document.addEventListener('click', (e) => {
      const btn = e.target;
      if (btn && btn.classList && btn.classList.contains('remove-row')) {
        const tr = btn.closest('tr');
        if (tr) tr.remove();
      }
    });
  }

  function serializeDynamic() {
    // Labour
    const labour = qsa('#labourTable tbody tr').map(tr => ({
      category: (qs('.lab-category', tr)?.value || '').trim(),
      workers: toNum(qs('.lab-workers', tr)?.value),
      hours: toNum(qs('.lab-hours', tr)?.value),
      overtime_hours: toNum(qs('.lab-ot', tr)?.value),
      agency: (qs('.lab-agency', tr)?.value || '').trim(),
    })).filter(r => r.category && (r.workers > 0 || r.hours > 0 || r.overtime_hours > 0 || r.agency));

    // Machinery
    const machinery = qsa('#machineryTable tbody tr').map(tr => {
      const breakdownVal = (qs('.mach-breakdown', tr)?.value || 'No');
      return {
        equipment_name: (qs('.mach-name', tr)?.value || '').trim(),
        hours_used: toNum(qs('.mach-hours', tr)?.value),
        idle_hours: toNum(qs('.mach-idle', tr)?.value),
        fuel_consumed: toNum(qs('.mach-fuel', tr)?.value),
        breakdown: breakdownVal === 'Yes',
        breakdown_remarks: (qs('.mach-break-remarks', tr)?.value || '').trim(),
      };
    }).filter(r => r.equipment_name && (r.hours_used > 0 || r.idle_hours > 0 || r.fuel_consumed > 0 || r.breakdown));

    // QC
    const qc = qsa('#qcTable tbody tr').map(tr => ({
      test_type: (qs('.qc-type', tr)?.value || '').trim(),
      location: (qs('.qc-location', tr)?.value || '').trim(),
      test_value: (qs('.qc-value', tr)?.value || '').trim(),
      result: (qs('.qc-result', tr)?.value || 'Pass').trim(),
      engineer_name: (qs('.qc-engineer', tr)?.value || '').trim(),
    })).filter(r => r.test_type && (r.location || r.test_value || r.engineer_name));

    // Delays
    const delays = qsa('#delayTable tbody tr').map(tr => ({
      delay_type: (qs('.delay-type', tr)?.value || '').trim(),
      start_time: (qs('.delay-start', tr)?.value || '').trim(),
      end_time: (qs('.delay-end', tr)?.value || '').trim(),
      responsible_party: (qs('.delay-party', tr)?.value || '').trim(),
      impact_hours: toNum(qs('.delay-impact-hours', tr)?.value),
      impact_quantity: toNum(qs('.delay-impact-qty', tr)?.value),
      remarks: (qs('.delay-remarks', tr)?.value || '').trim(),
    })).filter(r => r.delay_type && (r.start_time || r.end_time || r.impact_hours || r.impact_quantity || r.remarks || r.responsible_party));

    qs('#labour_json').value = JSON.stringify(labour);
    qs('#machinery_json').value = JSON.stringify(machinery);
    qs('#qc_json').value = JSON.stringify(qc);
    qs('#delays_json').value = JSON.stringify(delays);

    // Man-hours
    const manHours = labour.reduce((acc, r) => acc + (toNum(r.workers) * (toNum(r.hours) + toNum(r.overtime_hours))), 0);
    const mh = qs('#summary_man_hours');
    if (mh) mh.textContent = manHours.toFixed(2);

    const delayHours = delays.reduce((acc, r) => acc + toNum(r.impact_hours), 0);
    const dh = qs('#summary_delay_hours');
    if (dh) dh.textContent = delayHours.toFixed(2);
  }

  // Wire listeners
  headerRequired.forEach(sel => {
    const el = qs(sel);
    if (!el) return;
    el.addEventListener('input', () => {
      const ok = headerComplete();
      setGatedEnabled(ok);
      recomputeActivitiesAndMaterials();
    });
    el.addEventListener('change', () => {
      const ok = headerComplete();
      setGatedEnabled(ok);
      recomputeActivitiesAndMaterials();
    });
  });

  qsa('input.activity-executed, input.activity-executed-time, select.activity-time-unit, input.activity-remarks, textarea.activity-remarks, input.mat-issued, input.mat-consumed').forEach(el => {
    el.addEventListener('input', recomputeActivitiesAndMaterials);
  });

  qsa('select.activity-time-unit').forEach(el => {
    el.addEventListener('change', () => {
      const row = el.closest('tr[data-activity-id]');
      if (!row || !window.ActivityUnits) {
        recomputeActivitiesAndMaterials();
        return;
      }
      const unit = window.ActivityUnits.normalizeUnit(el.value);
      const hoursPerDay = window.ActivityUnits.normalizeHoursPerDay(row.dataset.hoursPerDay, 8);
      const execHours = window.ActivityUnits.toNum(qs('input.activity-executed-hours', row)?.value);
      const input = qs('input.activity-executed-time', row);
      if (input) input.value = window.ActivityUnits.hoursToDisplay(execHours, unit, hoursPerDay).toFixed(3);
      recomputeActivitiesAndMaterials();
    });
  });

  wireDynamicTables();

  form.addEventListener('submit', (e) => {
    const ok = headerComplete();
    setGatedEnabled(ok);
    recomputeActivitiesAndMaterials();

    // Validate dynamic tables + serialize
    serializeDynamic();

    // Block submit if any invalid inputs
    const invalid = qsa('.invalid', form).filter(el => !el.disabled);
    if (!ok || invalid.length > 0) {
      e.preventDefault();
      const top = invalid[0] || qs('.invalid');
      if (top && top.scrollIntoView) top.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
  });

  // Initial
  setGatedEnabled(headerComplete());
  recomputeActivitiesAndMaterials();
  serializeDynamic();
})();
