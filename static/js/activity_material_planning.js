(function () {
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function parseJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || '{}');
    } catch {
      return null;
    }
  }

  const vendorsByMaterial = parseJsonScript('vendorsByMaterialJson') || {};
  const materialsById = parseJsonScript('materialsByIdJson') || {};
  const activityDataById = parseJsonScript('activityDataByIdJson') || {};
  const activityMaterialsByActivity = parseJsonScript('activityMaterialsByActivityJson') || {};

  function toNum(v) {
    const n = Number(String(v ?? '').trim());
    return Number.isFinite(n) ? n : 0;
  }

  function asDate(v) {
    const s = String(v || '').trim();
    if (!s) return null;
    // Accept DD/MM/YYYY and ISO YYYY-MM-DD
    let iso = s;
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) {
      const parts = s.split('/');
      const dd = parts[0];
      const mm = parts[1];
      const yyyy = parts[2];
      iso = `${yyyy}-${mm}-${dd}`;
    }
    const d = new Date(iso + 'T00:00:00');
    return Number.isFinite(d.getTime()) ? d : null;
  }

  function fmtDDMMYYYY(d) {
    if (!d) return '';
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  }


  function daysBetweenInclusive(start, end) {
    if (!start || !end) return null;
    const ms = end.getTime() - start.getTime();
    if (!Number.isFinite(ms)) return null;
    const days = Math.floor(ms / 86400000);
    return days >= 0 ? (days + 1) : null;
  }

  function rebuildVendorOptions(materialId, vendorSelect, selectedVendorId) {
    if (!vendorSelect) return;
    const list = vendorsByMaterial[String(materialId)] || [];
    const options = ['<option value="">(No vendor)</option>'];
    list.forEach(v => {
      const inactive = v.is_active === false;
      const label = inactive ? `${v.vendor_name} (inactive)` : v.vendor_name;
      const sel = String(v.id) === String(selectedVendorId) ? ' selected' : '';
      options.push(`<option value="${v.id}"${sel}>${label}</option>`);
    });
    vendorSelect.innerHTML = options.join('');
  }

  function setPill(pill, text, kind) {
    if (!pill) return;
    pill.textContent = String(text || '—');
    pill.classList.remove('ok', 'warn', 'neutral');
    pill.classList.add(kind || 'neutral');
  }

  async function postForm(url, formData) {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    });

    let data = null;
    try {
      data = await resp.json();
    } catch {
      data = null;
    }

    if (!resp.ok || !data || data.ok !== true) {
      const msg = (data && (data.error || data.detail)) ? (data.error || data.detail) : `Request failed (${resp.status})`;
      throw new Error(msg);
    }

    return data;
  }

  function wireConfigurePanel() {
    const panelTitle = document.getElementById('ampPanelTitle');
    const panelEmpty = document.getElementById('ampPanelEmpty');
    const panelForm = document.getElementById('ampPanelForm');
    const panelClose = document.getElementById('ampPanelClose');

    const activityIdInput = document.getElementById('ampActivityId');

    const startInput = document.getElementById('ampStartDate');
    const endInput = document.getElementById('ampEndDate');
    const plannedQtyInput = document.getElementById('ampPlannedQty');
    const unitInput = document.getElementById('ampUnit');

    const plannedTimeDisplay = document.getElementById('ampPlannedTimeDisplay');
    const plannedTimeHours = document.getElementById('ampPlannedTimeHours');
    const displayUnitSel = document.getElementById('ampDisplayUnit');
    const hoursPerDayInput = document.getElementById('ampHoursPerDay');
    const hpdHelper = document.getElementById('ampHpdHelper');

    const materialSel = document.getElementById('ampMaterialId');
    const requiredQtyInput = document.getElementById('ampRequiredQty');
    const vendorSel = document.getElementById('ampVendorId');

    const leadTimePill = document.getElementById('ampLeadTimePill');
    const orderDatePill = document.getElementById('ampOrderDatePill');
    const orderStatusPill = document.getElementById('ampOrderStatusPill');
    const saveHint = document.getElementById('ampSaveHint');
    const reorderHint = document.getElementById('ampReorderHint');
    const linkedMaterials = document.getElementById('ampLinkedMaterials');

    const clearBtn = document.getElementById('ampClearBtn');
    const saveBtn = document.getElementById('ampSaveBtn');

    const lockBanner = document.getElementById('ampLockBanner');
    const adminUnlockWrap = document.getElementById('ampAdminUnlock');
    const unlockCheckbox = document.getElementById('ampUnlockCheckbox');
    const unlockReason = document.getElementById('ampUnlockReason');
    const unlockOverride = document.getElementById('ampUnlockOverride');

    let selectedActivityId = null;

    function setLockedUi(locked, progressPct) {
      const isLocked = Boolean(locked);
      const isAdmin = Boolean(adminUnlockWrap);

      if (lockBanner) {
        lockBanner.style.display = isLocked ? 'inline-block' : 'none';
        if (isLocked) {
          lockBanner.textContent = `Planning locked (progress: ${Number(progressPct || 0)}%). Baseline fields are read-only.`;
        }
      }

      // Baseline planning fields
      const baselineEls = [startInput, endInput, plannedQtyInput, unitInput, plannedTimeDisplay, displayUnitSel, hoursPerDayInput, materialSel, requiredQtyInput, vendorSel];
      baselineEls.forEach(el => {
        if (!el) return;
        el.disabled = isLocked;
      });

      if (adminUnlockWrap) {
        adminUnlockWrap.style.display = isLocked ? 'block' : 'none';
      }

      if (unlockCheckbox) {
        unlockCheckbox.checked = false;
      }
      if (unlockReason) {
        unlockReason.value = '';
        unlockReason.disabled = true;
      }
      if (unlockOverride) {
        unlockOverride.value = '0';
      }

      if (saveBtn) {
        // Non-admin cannot save locked activities. Admin must explicitly unlock per save.
        saveBtn.disabled = isLocked ? true : false;
        if (isLocked && isAdmin) {
          saveBtn.disabled = true;
        }
      }
      if (saveHint) {
        if (isLocked && !isAdmin) saveHint.textContent = 'Locked: execution started (Admin unlock required).';
        else if (isLocked && isAdmin) saveHint.textContent = 'Locked: enable Admin unlock to edit.';
      }
    }

    function applyAdminUnlockToggle() {
      if (!adminUnlockWrap || !unlockCheckbox) return;
      const enabled = unlockCheckbox.checked === true;

      const baselineEls = [startInput, endInput, plannedQtyInput, unitInput, plannedTimeDisplay, displayUnitSel, hoursPerDayInput, materialSel, requiredQtyInput, vendorSel];
      baselineEls.forEach(el => {
        if (!el) return;
        el.disabled = !enabled;
      });

      if (unlockReason) {
        unlockReason.disabled = !enabled;
      }
      if (unlockOverride) {
        unlockOverride.value = enabled ? '1' : '0';
      }
      if (saveBtn) {
        saveBtn.disabled = !enabled;
      }
      if (saveHint && enabled) {
        saveHint.textContent = 'Admin unlock enabled for this save.';
      }
    }

    function clearMaterialFields() {
      if (materialSel) materialSel.value = '';
      if (requiredQtyInput) requiredQtyInput.value = '';
      if (vendorSel) vendorSel.value = '';
      rebuildVendorOptions('', vendorSel, '');
      if (reorderHint) reorderHint.textContent = '';
      if (saveHint) saveHint.textContent = '—';
      setPill(leadTimePill, '⏱ LT: —', 'neutral');
      setPill(orderDatePill, '📦 Order: —', 'neutral');
      setPill(orderStatusPill, '—', 'neutral');
      if (requiredQtyInput) requiredQtyInput.required = false;
    }

    function updateSummary() {
      const s = asDate(startInput?.value);
      const e = asDate(endInput?.value);
      const dur = daysBetweenInclusive(s, e);
      const sumStart = document.getElementById('ampSummaryStart');
      const sumEnd = document.getElementById('ampSummaryEnd');
      const sumDuration = document.getElementById('ampSummaryDuration');
      if (sumStart) sumStart.textContent = startInput?.value ? String(startInput.value) : '—';
      if (sumEnd) sumEnd.textContent = endInput?.value ? String(endInput.value) : '—';
      if (sumDuration) sumDuration.textContent = (dur != null) ? `${dur} day${dur === 1 ? '' : 's'}` : '—';
    }

    function recomputeTimeFields() {
      if (!window.ActivityUnits) return;
      const displayUnit = (displayUnitSel && displayUnitSel.value) || 'hours';
      const hpd = window.ActivityUnits.normalizeHoursPerDay(hoursPerDayInput?.value, 8);
      if (hpdHelper) hpdHelper.textContent = `1 day = ${hpd} working hours`;

      const baseHours = window.ActivityUnits.displayToHours(plannedTimeDisplay?.value, displayUnit, hpd);
      if (plannedTimeHours) plannedTimeHours.value = String(baseHours);
    }

    function computeEffectiveLeadTimeDays() {
      const matId = String(materialSel?.value || '').trim();
      if (!matId) return null;
      const list = vendorsByMaterial[String(matId)] || [];
      const vid = String(vendorSel?.value || '').trim();
      if (vid) {
        const v = list.find(x => String(x.id) === String(vid));
        if (v) return Number.isFinite(Number(v.lead_time_days)) ? Number(v.lead_time_days) : 0;
      }
      const m = materialsById[String(matId)] || materialsById[Number(matId)] || null;
      if (m && m.default_lead_time_days != null) return Number(m.default_lead_time_days) || 0;
      return 0;
    }

    function computeAndRenderMaterialPreview() {
      const matId = String(materialSel?.value || '').trim();
      const lt = computeEffectiveLeadTimeDays();

      if (!matId) {
        setPill(leadTimePill, '⏱ LT: —', 'neutral');
        setPill(orderDatePill, '📦 Order: —', 'neutral');
        setPill(orderStatusPill, '—', 'neutral');
        if (requiredQtyInput) requiredQtyInput.required = false;
        return;
      }

      if (requiredQtyInput) requiredQtyInput.required = true;

      const start = asDate(startInput?.value);
      const lead = Number.isFinite(Number(lt)) ? Number(lt) : 0;
      setPill(leadTimePill, `⏱ LT: ${lead} day${lead === 1 ? '' : 's'}`, 'neutral');

      if (!start) {
        setPill(orderDatePill, '📦 Order: —', 'neutral');
        setPill(orderStatusPill, '—', 'neutral');
        return;
      }

      const orderDate = new Date(start.getTime() - (lead * 86400000));
      const today = new Date();
      const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      const orderDateDate = new Date(orderDate.getFullYear(), orderDate.getMonth(), orderDate.getDate());

      setPill(orderDatePill, `📦 Order: ${fmtDDMMYYYY(orderDateDate)}`, 'neutral');

      const diff = Math.floor((todayDate.getTime() - orderDateDate.getTime()) / 86400000);
      if (orderDateDate.getTime() < todayDate.getTime()) {
        setPill(orderStatusPill, `⚠ Late (${Math.max(diff, 0)}d)`, 'warn');
      } else {
        setPill(orderStatusPill, '✔ OK', 'ok');
      }
    }

    function renderLinkedMaterials(activityId) {
      if (!linkedMaterials) return;
      const rows = activityMaterialsByActivity[String(activityId)] || activityMaterialsByActivity[Number(activityId)] || [];
      if (!rows || rows.length === 0) {
        linkedMaterials.textContent = '—';
        return;
      }
      const chips = rows.slice(0, 8).map(r => {
        const name = r.material || 'Material';
        const req = (r.required_qty != null) ? Number(r.required_qty).toFixed(3) : '';
        const stock = (r.available_qty != null) ? Number(r.available_qty).toFixed(3) : '';
        const label = r.order_status && r.order_status.label ? r.order_status.label : '';
        const title = `Req: ${req}  Stock: ${stock}`;
        return `<span class="badge" title="${title}">${name}${req ? ` · ${req}` : ''}</span>`;
      }).join(' ');

      const more = rows.length > 8 ? ` <span class="badge badge-info">+${rows.length - 8} more</span>` : '';
      linkedMaterials.innerHTML = `${chips}${more}<div class="help-text" style="margin-top:8px">Tip: edit one requirement at a time in section B.</div>`;
    }

    function setRowActive(activityId) {
      $all('tr[data-activity-id]').forEach(r => {
        r.classList.toggle('is-active', String(r.getAttribute('data-activity-id')) === String(activityId));
      });
    }

    function updateRowStatus(activityId, isLinked) {
      const row = document.querySelector(`tr[data-activity-id="${activityId}"]`);
      if (!row) return;
      const cell = row.querySelector('td.amp-col-status');
      if (!cell) return;
      if (isLinked) {
        cell.innerHTML = '<span class="amp-badge linked" title="Planned and materials linked">🧷 Linked</span>';
      } else {
        cell.innerHTML = '<span class="amp-badge planned" title="Planned schedule/qty saved">🗓 Planned</span>';
      }
    }

    function openActivity(activityId) {
      selectedActivityId = String(activityId);

      const data = activityDataById[String(activityId)] || activityDataById[Number(activityId)] || null;
      if (!data) return;

      // Planning lock
      setLockedUi(Boolean(data.planning_locked), Number(data.progress_percent || 0));

      if (panelTitle) panelTitle.textContent = data.name || `Activity #${activityId}`;
      if (panelEmpty) panelEmpty.style.display = 'none';
      if (panelForm) panelForm.style.display = '';
      if (panelClose) panelClose.style.display = '';
      if (activityIdInput) activityIdInput.value = String(activityId);
      setRowActive(activityId);

      if (startInput) {
        const ds = asDate(data.start_date);
        startInput.value = ds ? fmtDDMMYYYY(ds) : '';
      }
      if (endInput) {
        const de = asDate(data.end_date);
        endInput.value = de ? fmtDDMMYYYY(de) : '';
      }
      if (plannedQtyInput) plannedQtyInput.value = String(data.planned_quantity || '');
      if (unitInput) unitInput.value = String(data.unit || '');

      if (plannedTimeDisplay) plannedTimeDisplay.value = String(toNum(data.planned_time_display).toFixed(3));
      if (plannedTimeHours) plannedTimeHours.value = String(toNum(data.planned_quantity_hours));
      if (displayUnitSel) displayUnitSel.value = String(data.display_unit || 'hours');
      if (hoursPerDayInput) hoursPerDayInput.value = String(toNum(data.hours_per_day || 8));

      updateSummary();
      recomputeTimeFields();
      renderLinkedMaterials(activityId);

      // Prefill requirement if exactly one linked row exists.
      const rows = activityMaterialsByActivity[String(activityId)] || activityMaterialsByActivity[Number(activityId)] || [];
      clearMaterialFields();
      if (rows && rows.length === 1) {
        const r = rows[0];
        if (materialSel && r.material_id) materialSel.value = String(r.material_id);
        rebuildVendorOptions(materialSel?.value, vendorSel, r.vendor_id || '');
        if (vendorSel && r.vendor_id) vendorSel.value = String(r.vendor_id);
        if (requiredQtyInput && r.required_qty != null) requiredQtyInput.value = String(r.required_qty);
      } else {
        rebuildVendorOptions('', vendorSel, '');
      }
      computeAndRenderMaterialPreview();
    }

    if (unlockCheckbox) {
      unlockCheckbox.addEventListener('change', applyAdminUnlockToggle);
    }

    function closePanel() {
      selectedActivityId = null;
      if (panelTitle) panelTitle.textContent = 'Select an activity';
      if (panelEmpty) panelEmpty.style.display = '';
      if (panelForm) panelForm.style.display = 'none';
      if (panelClose) panelClose.style.display = 'none';
      $all('tr[data-activity-id]').forEach(r => r.classList.remove('is-active'));
    }

    // Wire configure buttons
    $all('button.amp-configure').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-activity-id');
        if (id) openActivity(id);
      });
    });

    if (panelClose) panelClose.addEventListener('click', closePanel);

    // Live updates
    [startInput, endInput].forEach(el => el && el.addEventListener('change', () => {
      updateSummary();
      computeAndRenderMaterialPreview();
    }));
    [plannedTimeDisplay, displayUnitSel, hoursPerDayInput].forEach(el => el && el.addEventListener('input', () => {
      recomputeTimeFields();
    }));
    if (displayUnitSel) displayUnitSel.addEventListener('change', recomputeTimeFields);

    if (materialSel) materialSel.addEventListener('change', () => {
      rebuildVendorOptions(materialSel.value, vendorSel, '');
      if (vendorSel) vendorSel.value = '';
      computeAndRenderMaterialPreview();
    });
    if (vendorSel) vendorSel.addEventListener('change', computeAndRenderMaterialPreview);

    if (clearBtn) clearBtn.addEventListener('click', () => {
      clearMaterialFields();
      computeAndRenderMaterialPreview();
    });

    if (panelForm) {
      panelForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedActivityId) return;

        // If admin unlock section is visible, require unlock to save.
        if (adminUnlockWrap && adminUnlockWrap.style.display !== 'none') {
          if (!unlockCheckbox || unlockCheckbox.checked !== true) {
            alert('This activity is locked. Enable Admin unlock to save changes.');
            return;
          }
          const r = String(unlockReason?.value || '').trim();
          if (!r) {
            alert('Unlock reason is required.');
            return;
          }
        }

        if (saveBtn) saveBtn.disabled = true;
        if (saveHint) saveHint.textContent = 'Saving…';
        if (reorderHint) reorderHint.textContent = '';

        try {
          recomputeTimeFields();

          // Validate requirement fields
          const matId = String(materialSel?.value || '').trim();
          const req = String(requiredQtyInput?.value || '').trim();
          if (matId && !req) {
            throw new Error('Enter Material Required (or clear the material selection).');
          }

          const fd = new FormData(panelForm);

          if (!matId) {
            fd.delete('required_qty');
            fd.delete('vendor_id');
          }

          const data = await postForm('/activity-material-planning/save', fd);

          // Update pills from server response
          if (data && data.order_date) {
            const od = asDate(data.order_date);
            setPill(orderDatePill, `📦 Order: ${od ? fmtDDMMYYYY(od) : data.order_date}`, 'neutral');
          }
          if (data && data.order_status) {
            const kind = data.order_status.kind === 'LATE' ? 'warn' : (data.order_status.kind ? 'ok' : 'neutral');
            const label = data.order_status.kind === 'LATE' ? (data.order_status.label || '⚠ Late') : '✔ OK';
            setPill(orderStatusPill, label, kind);
          } else {
            setPill(orderStatusPill, '✔ Saved', 'ok');
          }

          if (reorderHint) reorderHint.textContent = data && data.reorder_hint ? String(data.reorder_hint) : '';
          if (saveHint) saveHint.textContent = 'Saved';

          // Update row status + linked list cache
          const isLinked = !!(data && data.mapping_id);
          updateRowStatus(selectedActivityId, isLinked);

          if (isLinked && matId) {
            const actKey = String(selectedActivityId);
            const arr = activityMaterialsByActivity[actKey] || [];
            const existingIdx = arr.findIndex(x => String(x.material_id) === String(matId));
            const mat = materialsById[String(matId)] || null;
            const rowObj = {
              material_id: Number(matId),
              material: mat ? mat.name : 'Material',
              unit: mat ? (mat.unit || '') : '',
              vendor_id: String(vendorSel?.value || '').trim() || null,
              required_qty: toNum(requiredQtyInput?.value),
              available_qty: null,
              reorder_hint: data.reorder_hint || null,
              order_date_suggested: data.order_date || null,
              order_status: data.order_status || null
            };
            if (existingIdx >= 0) arr[existingIdx] = Object.assign({}, arr[existingIdx], rowObj);
            else arr.push(rowObj);
            activityMaterialsByActivity[actKey] = arr;
            renderLinkedMaterials(selectedActivityId);
          }

        } catch (err) {
          if (saveHint) saveHint.textContent = '⚠ Save failed';
          alert(err && err.message ? err.message : 'Save failed');
        } finally {
          if (saveBtn) saveBtn.disabled = false;
        }
      });
    }

    // Esc closes panel
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closePanel();
    });
  }

  function bindMaterialMasterForms() {
    $all('form.mm-update-form').forEach(form => {
      const hint = $('.mm-save-hint', form);
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (hint) {
          hint.textContent = 'Saving…';
          hint.style.color = '';
        }
        try {
          const resp = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form)
          });
          if (!resp.ok) throw new Error(`Save failed (${resp.status})`);
          if (hint) {
            hint.textContent = 'Saved';
            hint.style.color = '#22c55e';
            setTimeout(() => { hint.textContent = ''; }, 1200);
          }
        } catch (err) {
          if (hint) {
            hint.textContent = 'Failed';
            hint.style.color = '#d64545';
          }
        }
      });
    });
  }

  function wireModal() {
    const modal = document.getElementById('vendorModal');
    const frame = document.getElementById('vendorModalFrame');

    window.openVendorModal = function (url) {
      if (!modal || !frame) return;
      frame.src = url;
      modal.style.display = 'flex';
    };

    window.closeVendorModal = function () {
      if (!modal || !frame) return;
      modal.style.display = 'none';
      frame.src = '';
    };

    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) window.closeVendorModal();
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') window.closeVendorModal();
    });
  }

  function bindSearchFilters() {
    const activitySearch = document.getElementById('ampActivitySearch');
    const materialSearch = document.getElementById('ampMaterialSearch');

    function norm(s) {
      return String(s || '').toLowerCase().trim();
    }

    if (activitySearch) {
      const activityRows = $all('tr[data-activity-id]');
      activitySearch.addEventListener('input', () => {
        const q = norm(activitySearch.value);
        activityRows.forEach(row => {
          const text = norm(row.textContent);
          row.style.display = (!q || text.includes(q)) ? '' : 'none';
        });
      });
    }

    if (materialSearch) {
      // Material Master rows (first table inside the details body)
      const master = document.getElementById('ampMaterialMaster');
      const rows = master ? $all('table.table tbody tr', master) : [];
      materialSearch.addEventListener('input', () => {
        const q = norm(materialSearch.value);
        rows.forEach(row => {
          const text = norm(row.textContent);
          row.style.display = (!q || text.includes(q)) ? '' : 'none';
        });
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    wireConfigurePanel();
    bindMaterialMasterForms();
    wireModal();
    bindSearchFilters();
  });
})();
