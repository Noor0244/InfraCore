/* InfraCore: Auto Units System
 * - When a material is selected, fetch /materials/{id}/units
 * - Auto-select standard unit
 * - Populate unit dropdown with allowed units
 * - Never uses alert()
 */

(function () {
    const DEFAULT_UNIT_CHOICES = ["Bags", "Kg", "MT", "Cum", "Ton", "Nos", "Ltr"];

    function isSelect(el) {
        return el && el.tagName === "SELECT";
    }

    function toOptionHtml(value, selected) {
        const safe = String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
        return `<option value="${safe}"${selected ? " selected" : ""}>${safe}</option>`;
    }

    function setSelectOptions(selectEl, values, selectedValue) {
        const list = Array.isArray(values) && values.length ? values : DEFAULT_UNIT_CHOICES;
        const selected = selectedValue && list.includes(selectedValue) ? selectedValue : list[0];

        selectEl.innerHTML = list.map(v => toOptionHtml(v, v === selected)).join("");
        selectEl.value = selected;
    }

    function ensureHelper(unitSelect) {
        const form = unitSelect.closest("form") || document;
        let helper = form.querySelector('[data-unit-helper][data-for="' + unitSelect.name + '"]');
        if (helper) return helper;

        // Try nearby container first
        const container = unitSelect.closest(".form-group") || unitSelect.parentElement;
        helper = container ? container.querySelector("[data-unit-helper]") : null;
        if (helper) return helper;

        helper = document.createElement("div");
        helper.className = "help-text";
        helper.setAttribute("data-unit-helper", "1");
        helper.setAttribute("data-for", unitSelect.name || "unit");
        helper.style.marginTop = "6px";
        if (container) container.appendChild(helper);
        return helper;
    }

    function findUnitSelectForMaterialSelect(materialSelect) {
        const form = materialSelect.closest("form") || document;

        // Prefer explicit opt-in
        const explicit = form.querySelector("[data-unit-select]");
        if (isSelect(explicit)) return explicit;

        // Common patterns
        const byName = form.querySelector('select[name="unit"], select[name$="_unit"], select[id*="unit"], select[id*="Unit"]');
        if (isSelect(byName)) return byName;

        return null;
    }

    async function fetchUnitConfig(materialId) {
        const res = await fetch(`/materials/${materialId}/units`, {
            headers: { "Accept": "application/json" },
            credentials: "same-origin"
        });

        if (!res.ok) throw new Error("Failed to fetch units");
        const data = await res.json();

        const allowed = Array.isArray(data.allowed_units) && data.allowed_units.length
            ? data.allowed_units
            : DEFAULT_UNIT_CHOICES;

        const standard = data.standard_unit && allowed.includes(data.standard_unit)
            ? data.standard_unit
            : allowed[0];

        return { standard_unit: standard, allowed_units: allowed };
    }

    async function applyAutoUnits(materialSelect) {
        const materialId = materialSelect.value;
        const unitSelect = findUnitSelectForMaterialSelect(materialSelect);
        if (!unitSelect) return;

        const helper = ensureHelper(unitSelect);

        // If cleared, reset to safe defaults
        if (!materialId) {
            setSelectOptions(unitSelect, DEFAULT_UNIT_CHOICES, DEFAULT_UNIT_CHOICES[0]);
            if (helper) helper.textContent = "";
            return;
        }

        try {
            const cfg = await fetchUnitConfig(materialId);
            setSelectOptions(unitSelect, cfg.allowed_units, cfg.standard_unit);
            if (helper) {
                helper.textContent = "Standard unit applied. You can change it if required.";
            }
        } catch (e) {
            // Fallback safety: do not break form
            setSelectOptions(unitSelect, DEFAULT_UNIT_CHOICES, unitSelect.value || DEFAULT_UNIT_CHOICES[0]);
            if (helper) {
                helper.textContent = "";
            }
        }
    }

    function isMaterialSelect(el) {
        if (!isSelect(el)) return false;
        if (el.hasAttribute("data-material-select")) return true;

        // Common conventions used across InfraCore JS
        const name = (el.getAttribute("name") || "").toLowerCase();
        const id = (el.getAttribute("id") || "").toLowerCase();

        return name === "material_id" || name.endsWith("material_id") || id.includes("material") && !id.includes("materials");
    }

    function initExisting() {
        document.querySelectorAll("select").forEach(sel => {
            if (!isMaterialSelect(sel)) return;
            // If a material is pre-selected (edit pages), apply units immediately.
            if (sel.value) applyAutoUnits(sel);
        });
    }

    document.addEventListener("change", (e) => {
        const target = e.target;
        if (!isMaterialSelect(target)) return;
        applyAutoUnits(target);
    });

    document.addEventListener("DOMContentLoaded", initExisting);

    // Expose a small API for dynamically injected forms/modals
    window.InfraCoreAutoUnits = {
        refresh: initExisting,
        applyFor: applyAutoUnits
    };
})();
