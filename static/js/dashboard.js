document.addEventListener("DOMContentLoaded", () => {

    /* ================= PROJECT CONTEXT ================= */
    const projectIdEl = document.getElementById('projectIdJson');
    const projectIdFromJson = projectIdEl ? JSON.parse(projectIdEl.textContent || 'null') : null;
    const projectId =
        projectIdFromJson !== null && typeof projectIdFromJson !== 'undefined'
            ? Number(projectIdFromJson)
            : (typeof window.PROJECT_ID !== "undefined" && window.PROJECT_ID !== null
                ? Number(window.PROJECT_ID)
                : null);

    /* ================= DOM REFERENCES ================= */

    const totalActivities = document.getElementById("totalActivities");
    const inProgressActivities = document.getElementById("inProgressActivities");
    const completedActivities = document.getElementById("completedActivities");
    const delayedActivities = document.getElementById("delayedActivities");
    const materialRiskActivities = document.getElementById("materialRiskActivities");
    const overallProgressBar = document.getElementById("overallProgressBar");

    const timeUnitSelect = document.getElementById("timeUnitSelect");
    const timePlanned = document.getElementById("timePlanned");
    const timeExecuted = document.getElementById("timeExecuted");
    const timeUnitLabel = document.getElementById("timeUnitLabel");
    const timeUnitLabel2 = document.getElementById("timeUnitLabel2");
    const overallTimeProgress = document.getElementById("overallTimeProgress");

    const activityTableBody = document.getElementById("activityTableBody");
    const addActivityBtn = document.getElementById("addActivityBtn");

    const progressModal = document.getElementById("progressModal");
    const progressForm = document.getElementById("progressForm");
    const progressActivityId = document.getElementById("progressActivityId");
    const progressPercentInput = document.getElementById("progressPercentInput");

    const planModal = document.getElementById("planModal");
    const planForm = document.getElementById("planForm");
    const planActivitySelect = document.getElementById("planActivitySelect");
    const planStart = document.getElementById("planStart");
    const planEnd = document.getElementById("planEnd");

    const materialUsageModal = document.getElementById("materialUsageModal");
    const materialUsageForm = document.getElementById("materialUsageForm");
    const usageActivityId = document.getElementById("usageActivityId");
    const usageMaterialSelect = document.getElementById("usageMaterialSelect");
    const usageQty = document.getElementById("usageQty");
    const usageDate = document.getElementById("usageDate");

    /* ================= BUTTON BINDINGS ================= */

    if (addActivityBtn) {
        addActivityBtn.addEventListener("click", openPlanModal);
    }

    /* ================= INITIAL LOAD ================= */

    if (!projectId) {
        if (activityTableBody) {
            activityTableBody.innerHTML =
                `<tr><td colspan="8">Create a project to start planning</td></tr>`;
        }
        return;
    }

    loadDashboard();
    loadActivities();

    if (timeUnitSelect) {
        timeUnitSelect.addEventListener('change', () => {
            loadDashboard();
        });
    }

    /* ================= DASHBOARD ================= */

    function loadDashboard() {
        const tu = timeUnitSelect ? String(timeUnitSelect.value || 'hours') : 'hours';
        const qs = tu ? `?time_unit=${encodeURIComponent(tu)}` : '';
        fetch(`/analytics/project-dashboard/${projectId}${qs}`)
            .then(r => r.ok ? r.json() : Promise.reject())
            .then(d => {
                totalActivities.innerText = d.activities.total;
                inProgressActivities.innerText = d.activities.in_progress;
                completedActivities.innerText = d.activities.completed;
                delayedActivities.innerText = d.activities.delayed;
                if (materialRiskActivities) {
                    materialRiskActivities.innerText = String(d.material_risk_activities ?? 0);
                }

                const progress = d.overall_progress_percent || 0;
                overallProgressBar.style.width = progress + "%";
                overallProgressBar.innerText = progress + "%";

                // Time KPIs (additive)
                const time = d.time || {};
                const display = time.display || {};
                const unit = display.unit || tu;
                const unitLabel = unit === 'days' ? 'days' : 'hrs';

                if (timePlanned) timePlanned.innerText = (display.planned ?? '–');
                if (timeExecuted) timeExecuted.innerText = (display.executed ?? '–');
                if (timeUnitLabel) timeUnitLabel.innerText = unitLabel;
                if (timeUnitLabel2) timeUnitLabel2.innerText = unitLabel;

                if (overallTimeProgress) {
                    overallTimeProgress.innerText = String(time.overall_progress_percent ?? 0) + '%';
                }
            })
            .catch(() => {
                console.warn("Dashboard analytics not available yet");
            });
    }

    /* ================= ACTIVITIES ================= */

    function loadActivities() {
        fetch(`/schedule/project/${projectId}`)
            .then(r => r.ok ? r.json() : [])
            .then(rows => {
                activityTableBody.innerHTML = "";

                if (!rows || rows.length === 0) {
                    activityTableBody.innerHTML =
                        `<tr><td colspan="8">No activities planned</td></tr>`;
                    return;
                }

                rows.forEach(r => {
                    const icon = r.material_icon ?? "—";
                    const status = r.material_status ?? "UNKNOWN";
                    const late = Number(r.material_days_late ?? 0);
                    const tip = status === 'LATE'
                        ? `Late by ${late} day(s)`
                        : status === 'PENDING'
                            ? 'Pending delivery'
                            : status === 'AVAILABLE'
                                ? 'Available before start'
                                : 'No material plan';

                    activityTableBody.insertAdjacentHTML("beforeend", `
                        <tr>
                            <td>${r.activity_id}</td>
                            <td>${r.planned_start}</td>
                            <td>${r.planned_end}</td>
                            <td>${r.progress_percent}%</td>
                            <td>${r.status}</td>
                            <td>${r.delay_days}</td>
                            <td>
                                <span title="${tip}" style="font-size:1.1em">${icon}</span>
                                <button style="margin-left:8px" onclick="openMaterialUsageModal(${r.activity_id})">Add Usage</button>
                            </td>
                            <td>
                                <button onclick="openProgressModal(${r.activity_id}, ${r.progress_percent})">
                                    Update
                                </button>
                            </td>
                        </tr>
                    `);
                });
            })
            .catch(() => {
                activityTableBody.innerHTML =
                    `<tr><td colspan="8">Failed to load activities</td></tr>`;
            });
    }

    /* ================= PLAN ACTIVITY ================= */

    window.openPlanModal = function () {
        if (!projectId) return;

        planModal.style.display = "block";
        planActivitySelect.innerHTML = `<option disabled selected>Loading...</option>`;

        fetch("/activities")
            .then(r => r.ok ? r.json() : [])
            .then(list => {
                planActivitySelect.innerHTML = "";
                list.forEach(a => {
                    planActivitySelect.insertAdjacentHTML(
                        "beforeend",
                        `<option value="${a.id}">${a.name}</option>`
                    );
                });
            });
    };

    window.closePlanModal = function () {
        planModal.style.display = "none";
    };

    planForm.addEventListener("submit", e => {
        e.preventDefault();

        fetch("/schedule/plan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: projectId,
                activity_id: planActivitySelect.value,
                planned_start: planStart.value,
                planned_end: planEnd.value
            })
        })
        .then(() => {
            closePlanModal();
            loadDashboard();
            loadActivities();
        });
    });

    /* ================= MATERIAL USAGE ================= */

    window.openMaterialUsageModal = function (activityId) {
        materialUsageModal.style.display = "block";
        usageActivityId.value = activityId;
        usageQty.value = "";
        usageDate.valueAsDate = new Date();
        usageMaterialSelect.innerHTML = "";

        fetch("/materials")
            .then(r => r.ok ? r.json() : [])
            .then(list => {
                list.forEach(m => {
                    usageMaterialSelect.insertAdjacentHTML(
                        "beforeend",
                        `<option value="${m.id}">${m.name}</option>`
                    );
                });
            });
    };

    window.closeMaterialUsageModal = function () {
        materialUsageModal.style.display = "none";
    };

    materialUsageForm.addEventListener("submit", e => {
        e.preventDefault();

        fetch("/daily-material-usage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: projectId,
                activity_id: usageActivityId.value,
                material_id: usageMaterialSelect.value,
                quantity_used: Number(usageQty.value),
                usage_date: usageDate.value
            })
        })
        .then(() => {
            closeMaterialUsageModal();
            loadDashboard();
        });
    });

    /* ================= PROGRESS ================= */

    window.openProgressModal = function (id, progress) {
        progressActivityId.value = id;
        progressPercentInput.value = progress;
        progressModal.style.display = "block";
    };

    window.closeProgressModal = function () {
        progressModal.style.display = "none";
    };

    progressForm.addEventListener("submit", e => {
        e.preventDefault();

        fetch("/schedule/progress", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_id: projectId,
                activity_id: progressActivityId.value,
                progress_percent: Number(progressPercentInput.value)
            })
        })
        .then(() => {
            closeProgressModal();
            loadDashboard();
            loadActivities();
        });
    });

});

/* ================= CREATE PROJECT (SAFE OVERRIDE) ================= */

/* 🔥 MODAL IS NO LONGER USED — REDIRECT INSTEAD */
window.openCreateProjectModal = function () {
    window.location.href = "/projects/new";
};

/* KEEPING THESE FOR SAFETY — NO REMOVAL */
const createProjectModal = document.getElementById("createProjectModal");
const createProjectForm = document.getElementById("createProjectForm");

window.closeCreateProjectModal = function () {
    if (createProjectModal) {
        createProjectModal.classList.remove("show");
    }
};

if (createProjectForm) {
    createProjectForm.addEventListener("submit", function (e) {
        e.preventDefault();
        window.location.href = "/projects/new";
    });
}
