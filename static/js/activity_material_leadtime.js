(function () {
  function $(sel, root) { return (root || document).querySelector(sel); }

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

  function rebuildVendorOptions(materialId, vendorSelect, selectedVendorId) {
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

  function getVendorLeadTime(materialId, vendorId) {
    const list = vendorsByMaterial[String(materialId)] || [];
    const v = list.find(x => String(x.id) === String(vendorId));
    return v ? Number(v.lead_time_days || 0) : 0;
  }

  function bindRow(row) {
    const materialId = row.getAttribute('data-material-id');
    const vendorSelect = $('.vendor-select', row);
    const ltInput = $('.leadtime-override', row);
    const ltHint = $('.leadtime-hint', row);

    if (!materialId || !vendorSelect) return;

    // initial options already rendered server-side, but keep in sync
    rebuildVendorOptions(materialId, vendorSelect, vendorSelect.value);

    function refreshHints() {
      const vid = vendorSelect.value;
      const vendorLt = vid ? getVendorLeadTime(materialId, vid) : null;
      const overrideRaw = ltInput ? String(ltInput.value || '').trim() : '';
      const override = overrideRaw === '' ? null : Number(overrideRaw);

      if (!ltHint) return;

      if (override !== null && vendorLt !== null && Math.abs(override - vendorLt) > 1e-9) {
        ltHint.textContent = `Override active. Vendor lead time is ${vendorLt} days.`;
        ltHint.style.color = '#d64545';
      } else if (vid) {
        ltHint.textContent = `Vendor lead time: ${vendorLt} days.`;
        ltHint.style.color = '';
      } else {
        ltHint.textContent = 'No vendor selected.';
        ltHint.style.color = '';
      }
    }

    vendorSelect.addEventListener('change', () => {
      // If override is empty, we just show vendor LT hint.
      refreshHints();
    });

    if (ltInput) {
      ltInput.addEventListener('input', refreshHints);
    }

    refreshHints();
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('tr.activity-material-row').forEach(bindRow);

    // Add-form auto-fill
    const addForm = document.getElementById('addMappingForm');
    if (addForm) {
      const matSel = $('#add_material_id', addForm);
      const vendSel = $('#add_vendor_id', addForm);
      const ltHint = $('#add_leadtime_hint', addForm);
      const ltOverride = $('#add_leadtime_override', addForm);

      function refreshAdd() {
        if (!matSel || !vendSel) return;
        rebuildVendorOptions(matSel.value, vendSel, vendSel.value);

        const vid = vendSel.value;
        const vendorLt = vid ? getVendorLeadTime(matSel.value, vid) : null;
        if (ltHint) {
          if (vid) {
            ltHint.textContent = `Vendor lead time: ${vendorLt} days.`;
          } else {
            ltHint.textContent = 'Select a vendor to use vendor lead time.';
          }
        }

        if (ltOverride) {
          const overrideRaw = String(ltOverride.value || '').trim();
          if (overrideRaw !== '' && vendorLt !== null && Math.abs(Number(overrideRaw) - vendorLt) > 1e-9) {
            ltHint.style.color = '#d64545';
          } else {
            ltHint.style.color = '';
          }
        }
      }

      if (matSel) matSel.addEventListener('change', refreshAdd);
      if (vendSel) vendSel.addEventListener('change', refreshAdd);
      if (ltOverride) ltOverride.addEventListener('input', refreshAdd);

      refreshAdd();
    }
  });
})();
