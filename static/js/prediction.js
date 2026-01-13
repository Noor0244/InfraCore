(function () {
  const shell = document.getElementById('predShell');
  const cfg = (window.__PRED && typeof window.__PRED === 'object') ? window.__PRED : {};
  const projectId = Number(cfg.projectId || shell?.dataset?.projectId || 0);
  if (!projectId) return;
  const isRoad = !!(cfg.isRoad || (shell?.dataset?.isRoad === '1'));

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  const modeRow = qs('#modeRow');
  const btnRecalc = qs('#btnRecalc');
  const autoRefresh = qs('#autoRefresh');

  const riskBadge = qs('#riskBadge');
  const kpiStockout = qs('#kpiStockout');
  const kpiReorder = qs('#kpiReorder');
  const kpiDelay = qs('#kpiDelay');
  const kpiCost = qs('#kpiCost');

  const alertsBox = qs('#alerts');
  const historyList = qs('#historyList');

  const chartMaterial = qs('#chartMaterial');
  const chartMaterial2 = qs('#chartMaterial2');

  let activeMode = 'Inventory';
  let lastLogId = null;

  let chartInv = null;
  let chartCons = null;

  function setRisk(risk) {
    const r = String(risk || 'Low');
    riskBadge.textContent = `${r} Risk`;
    riskBadge.classList.remove('low', 'medium', 'high');
    if (r === 'High') riskBadge.classList.add('high');
    else if (r === 'Medium') riskBadge.classList.add('medium');
    else riskBadge.classList.add('low');
  }

  function fmtMoney(v) {
    const n = Number(v || 0);
    if (!isFinite(n)) return '–';
    return n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  function setMode(m) {
    activeMode = m;
    qsa('.mode-btn', modeRow).forEach(b => b.classList.toggle('active', b.dataset.mode === m));
    if (autoRefresh && autoRefresh.value === 'on') recalc();
  }

  function collectInputs() {
    const horizonDays = Number(qs('#horizonDays')?.value || 14);

    if (isRoad) {
      return {
        chainage_progress_rate: Number(qs('#chainageRate')?.value || 0),
        road_layer: qs('#roadLayer')?.value || '',
        lead_time_buffer_days: Number(qs('#leadBufferRoad')?.value || 0),
        safety_stock_pct: Number(qs('#safetyPctRoad')?.value || 0),
        weather_impact_factor: Number(qs('#weatherImpact')?.value || 0),
        horizon_days: horizonDays,
      };
    }

    return {
      floor_progress_rate: Number(qs('#floorRate')?.value || 0),
      activity_id: qs('#activityId')?.value || '',
      lead_time_buffer_days: Number(qs('#leadBufferBldg')?.value || 0),
      safety_stock_pct: Number(qs('#safetyPctBldg')?.value || 0),
      horizon_days: horizonDays,
    };
  }

  function renderAlerts(items) {
    alertsBox.innerHTML = '';
    const arr = Array.isArray(items) ? items : [];
    if (!arr.length) {
      const div = document.createElement('div');
      div.className = 'alert';
      div.innerHTML = '<div class="msg">No critical alerts</div><div class="meta">Risk signals will appear as usage data grows.</div>';
      alertsBox.appendChild(div);
      return;
    }

    for (const a of arr) {
      const div = document.createElement('div');
      div.className = 'alert';
      div.innerHTML = `<div class="msg">${a.message || ''}</div><div class="meta">Material: ${a.material || ''} · Risk: ${a.risk || ''}</div>`;
      alertsBox.appendChild(div);
    }
  }

  function ensureCharts() {
    const ctx1 = qs('#chartInventoryTime');
    const ctx2 = qs('#chartConsumption');
    if (!ctx1 || !ctx2 || !window.Chart) return;

    if (!chartInv) {
      chartInv = new Chart(ctx1, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Predicted Stock', data: [], borderColor: '#1e6fd8', backgroundColor: 'rgba(30,111,216,0.15)', tension: 0.25, fill: true }] },
        options: {
          responsive: true,
          plugins: { legend: { display: true } },
          scales: { x: { ticks: { maxTicksLimit: 6 } }, y: { beginAtZero: true } },
        }
      });
    }

    if (!chartCons) {
      chartCons = new Chart(ctx2, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            { label: 'Predicted Daily Consumption', data: [], borderColor: '#9ca3af', backgroundColor: 'rgba(156,163,175,0.10)', tension: 0.25 },
            { label: 'Actual Daily Consumption', data: [], borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.12)', tension: 0.25 },
          ]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: true } },
          scales: { x: { ticks: { maxTicksLimit: 6 } }, y: { beginAtZero: true } },
        }
      });
    }
  }

  function updateCharts(charts) {
    ensureCharts();
    if (!chartInv || !chartCons) return;

    const inv = charts?.inventory_vs_time;
    if (!inv) return;

    const labels = inv.dates || [];
    chartInv.data.labels = labels;
    chartInv.data.datasets[0].data = inv.predicted_stock || [];
    chartInv.update();

    chartCons.data.labels = labels;
    chartCons.data.datasets[0].data = inv.predicted_consumption || [];
    chartCons.data.datasets[1].data = inv.actual_consumption || [];
    chartCons.update();
  }

  async function recalc() {
    const inputs = collectInputs();

    const res = await fetch(`/projects/${projectId}/prediction/calc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ mode: activeMode, inputs }),
    });

    if (!res.ok) {
      setRisk('Medium');
      kpiStockout.textContent = '–';
      kpiReorder.textContent = '–';
      kpiDelay.textContent = '–';
      kpiCost.textContent = '–';
      renderAlerts([{ message: 'Prediction calculation failed', material: '', risk: 'Medium' }]);
      return;
    }

    const data = await res.json();
    lastLogId = data.log_id || null;

    const s = data.summary || {};
    setRisk(s.risk);

    kpiStockout.textContent = s.predicted_stockout_date || '–';
    kpiReorder.textContent = s.reorder_date ? `${s.reorder_date} · ${s.recommendation || ''}` : '–';

    if (isRoad) {
      const dd = Number(s.delay_days || 0);
      const cl = Number(s.chainage_loss_km || 0);
      kpiDelay.textContent = `${dd.toFixed(1)} days · ${cl.toFixed(2)} km loss`;
    } else {
      const dd = Number(s.delay_days || 0);
      const fl = Number(s.floor_loss || 0);
      kpiDelay.textContent = `${dd.toFixed(1)} days · ${fl.toFixed(2)} floors loss`;
    }

    kpiCost.textContent = fmtMoney(s.cost_impact || 0);

    const tm = data.charts?.top_material;
    chartMaterial.textContent = tm ? `(${tm})` : '';
    chartMaterial2.textContent = tm ? `(${tm})` : '';

    renderAlerts(data.alerts);
    updateCharts(data.charts?.inventory_vs_time ? data.charts : null);

    await refreshHistory();
  }

  async function refreshHistory() {
    if (!historyList) return;
    const res = await fetch(`/projects/${projectId}/prediction/history`, { credentials: 'same-origin' });
    if (!res.ok) return;
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];

    historyList.innerHTML = '';
    if (!items.length) {
      const div = document.createElement('div');
      div.className = 'alert';
      div.innerHTML = '<div class="msg">No history yet</div><div class="meta">Run a prediction to create an audit trail.</div>';
      historyList.appendChild(div);
      return;
    }

    for (const it of items) {
      const div = document.createElement('div');
      div.className = 'alert';
      const t = it.created_at ? it.created_at.replace('T', ' ').slice(0, 19) : '';
      div.innerHTML = `<div class="msg">${it.mode || ''} · ${it.project_type || ''}</div><div class="meta">${t}${it.action_taken ? ' · Action: ' + it.action_taken : ''}</div>`;
      historyList.appendChild(div);
    }
  }

  async function sendAction(action) {
    if (!lastLogId) return;
    await fetch(`/projects/${projectId}/prediction/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ log_id: lastLogId, action_taken: action }),
    });
    await refreshHistory();
  }

  // Bind mode buttons
  qsa('.mode-btn', modeRow).forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));

  // Bind recalc
  btnRecalc?.addEventListener('click', recalc);

  // Auto-recalc on input changes
  qsa('input,select').forEach(el => {
    el.addEventListener('input', () => { if (autoRefresh?.value === 'on') recalc(); });
    el.addEventListener('change', () => { if (autoRefresh?.value === 'on') recalc(); });
  });

  // Actions
  qs('#actReorder')?.addEventListener('click', () => sendAction('Reorder now'));
  qs('#actSafety')?.addEventListener('click', () => sendAction('Increase safety stock'));
  qs('#actSupplier')?.addEventListener('click', () => sendAction('Change supplier'));

  // Init
  refreshHistory();
  recalc();
})();
