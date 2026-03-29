(function () {
  // Guard
  const role = sessionStorage.getItem("role");
  const username = sessionStorage.getItem("username");
  if (role !== "admin" || !username) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("navUser").textContent = username;
  document.getElementById("logoutBtn").addEventListener("click", () => {
    sessionStorage.clear();
    window.location.href = "index.html";
  });

  let allUsers = [];

  const STATUS_BADGES = {
    pending: "bg-warning text-dark",
    approved: "bg-success",
    rejected: "bg-danger",
    cancelled: "bg-secondary",
    completed: "bg-info text-dark",
  };

  const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "-");
  const esc = (v) => (v ? String(v).replace(/"/g, "&quot;").replace(/'/g, "&#39;") : "");
  const cut = (t, n = 40) => {
    if (!t) return "-";
    const s = typeof t === "object" ? JSON.stringify(t) : String(t);
    return s.length > n ? s.slice(0, n) + "\u2026" : s;
  };

  function showToast(msg, bg) {
    const el = document.getElementById("toast");
    const body = document.getElementById("toastBody");
    el.className = `toast align-items-center border-0 text-white ${bg}`;
    body.textContent = msg;
    new bootstrap.Toast(el, { delay: 3000 }).show();
  }

  // ── Searchable dropdown helper ──
  function setupUserDropdown(searchId, selectId, onChange) {
    const input = document.getElementById(searchId);
    const select = document.getElementById(selectId);

    function populate(filter) {
      const term = (filter || "").toLowerCase();
      const list = term ? allUsers.filter((u) => u.username.toLowerCase().includes(term)) : allUsers;
      const opts = list.map((u) => `<option value="${u.user_id}" data-name="${esc(u.username)}">${u.username}</option>`);
      select.innerHTML = `<option value="">-- Select a user --</option>` + opts.join("");
    }

    input.addEventListener("input", () => populate(input.value));
    select.addEventListener("change", () => {
      const opt = select.selectedOptions[0];
      if (opt && opt.value) onChange(opt.value, opt.dataset.name);
    });

    return populate;
  }

  // ══════════════════════════════
  //  Summary Cards
  // ══════════════════════════════

  async function loadCards() {
    let tasks = [];
    try { tasks = await api.getAllHITLTasks(); } catch {}
    const c = (s) => tasks.filter((t) => t.status === s).length;
    document.getElementById("countPending").textContent = c("pending");
    document.getElementById("countApproved").textContent = c("approved");
    document.getElementById("countRejected").textContent = c("rejected");
    document.getElementById("countCompleted").textContent = c("completed");
  }

  // ══════════════════════════════
  //  Tab 1 – Overview
  // ══════════════════════════════

  const populateOverview = setupUserDropdown("overviewUserSearch", "overviewUserSelect", async (id, name) => {
    document.getElementById("overviewUserLabel").textContent = `Task summary for ${name}`;
    document.getElementById("overviewTableSection").style.display = "";
    const body = document.getElementById("overviewBody");
    try {
      const tasks = await api.getHITLTasksByUser(id);
      const c = (s) => tasks.filter((t) => t.status === s).length;
      body.innerHTML = `<tr>
        <td>${name}</td>
        <td class="text-center">${c("pending")}</td>
        <td class="text-center">${c("approved")}</td>
        <td class="text-center">${c("rejected")}</td>
        <td class="text-center">${c("completed")}</td>
        <td class="text-center fw-bold">${tasks.length}</td>
      </tr>`;
    } catch {
      body.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Failed to load.</td></tr>`;
    }
  });

  // ══════════════════════════════
  //  Tab 2 – User Details
  // ══════════════════════════════

  let detailsTasks = [];
  const detailsRunsBody = document.getElementById("detailsRunsBody");
  const detailsTasksBody = document.getElementById("detailsTasksBody");
  const detailsFilter = document.getElementById("detailsStatusFilter");

  const populateDetails = setupUserDropdown("detailsUserSearch", "detailsUserSelect", async (id, name) => {
    document.getElementById("detailsUserLabel").textContent = name;
    document.getElementById("detailsSection").style.display = "";
    detailsFilter.value = "";
    await Promise.all([loadRuns(id), loadDetailTasks(id)]);
  });

  async function loadRuns(userId) {
    try {
      const runs = await api.getUserRunsByUser(userId);
      detailsRunsBody.innerHTML = runs.length
        ? runs.map((r) => `<tr>
            <td title="${r.user_run_id}">${cut(r.user_run_id, 12)}</td>
            <td title="${esc(r.message)}">${cut(r.message, 60)}</td>
            <td>${fmt(r.created_at)}</td>
          </tr>`).join("")
        : `<tr><td colspan="3" class="text-center text-muted">No runs found.</td></tr>`;
    } catch {
      detailsRunsBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">Failed to load.</td></tr>`;
    }
  }

  async function loadDetailTasks(userId) {
    try {
      detailsTasks = await api.getHITLTasksByUser(userId);
      renderDetailTasks();
    } catch {
      detailsTasksBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load.</td></tr>`;
    }
  }

  function renderDetailTasks() {
    const f = detailsFilter.value;
    const list = f ? detailsTasks.filter((t) => t.status === f) : detailsTasks;
    if (!list.length) {
      detailsTasksBody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">No tasks.</td></tr>`;
      return;
    }
    detailsTasksBody.innerHTML = list.map((t) => {
      const badge = STATUS_BADGES[t.status] || "bg-secondary";
      return `<tr>
        <td title="${t.hitl_task_id}">${cut(t.hitl_task_id, 12)}</td>
        <td>${t.task_name || "-"}</td>
        <td title="${esc(t.task_description)}">${cut(t.task_description, 30)}</td>
        <td class="task-args" title="${esc(t.task_args ? JSON.stringify(t.task_args) : "")}">${cut(t.task_args, 25)}</td>
        <td><span class="badge ${badge}">${t.status}</span></td>
        <td title="${esc(t.user_run_message)}">${cut(t.user_run_message, 30)}</td>
        <td title="${esc(t.output)}">${cut(t.output, 30)}</td>
        <td>${fmt(t.created_at)}</td>
        <td>${fmt(t.updated_at)}</td>
      </tr>`;
    }).join("");
  }

  detailsFilter.addEventListener("change", renderDetailTasks);

  // ══════════════════════════════
  //  Tab 3 – Approve Tasks
  // ══════════════════════════════

  let approveUserId = null;
  const approveBody = document.getElementById("approveBody");

  const populateApprove = setupUserDropdown("approveUserSearch", "approveUserSelect", async (id, name) => {
    approveUserId = id;
    document.getElementById("approveUserLabel").textContent = `Pending tasks for ${name}`;
    document.getElementById("approveSection").style.display = "";
    await loadPending();
  });

  async function loadPending() {
    if (!approveUserId) return;
    try {
      const tasks = await api.getHITLTasksByUser(approveUserId, "pending");
      if (!tasks.length) {
        approveBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No pending tasks.</td></tr>`;
        return;
      }
      approveBody.innerHTML = tasks.map((t) => `<tr>
        <td title="${t.hitl_task_id}">${cut(t.hitl_task_id, 12)}</td>
        <td>${t.task_name || "-"}</td>
        <td title="${esc(t.task_description)}">${cut(t.task_description, 30)}</td>
        <td class="task-args" title="${esc(t.task_args ? JSON.stringify(t.task_args) : "")}">${cut(t.task_args, 25)}</td>
        <td title="${esc(t.user_run_message)}">${cut(t.user_run_message, 30)}</td>
        <td>${fmt(t.created_at)}</td>
        <td class="text-center">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-success approve-btn" data-tid="${t.hitl_task_id}" data-rid="${t.user_run_id}"><i class="bi bi-check-lg"></i></button>
            <button class="btn btn-danger reject-btn" data-tid="${t.hitl_task_id}"><i class="bi bi-x-lg"></i></button>
          </div>
        </td>
      </tr>`).join("");

      approveBody.querySelectorAll(".approve-btn").forEach((btn) =>
        btn.addEventListener("click", async () => {
          btn.disabled = true;
          try {
            await api.approveTask(btn.dataset.tid, approveUserId, btn.dataset.rid);
            showToast("Task approved.", "bg-success");
            await Promise.all([loadPending(), loadCards()]);
          } catch (e) {
            showToast("Approve failed: " + e.message, "bg-danger");
            btn.disabled = false;
          }
        })
      );

      approveBody.querySelectorAll(".reject-btn").forEach((btn) =>
        btn.addEventListener("click", async () => {
          btn.disabled = true;
          try {
            await api.rejectTask(btn.dataset.tid);
            showToast("Task rejected.", "bg-warning");
            await Promise.all([loadPending(), loadCards()]);
          } catch (e) {
            showToast("Reject failed: " + e.message, "bg-danger");
            btn.disabled = false;
          }
        })
      );
    } catch {
      approveBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Failed to load.</td></tr>`;
    }
  }

  document.getElementById("approveRefreshBtn").addEventListener("click", loadPending);

  // ══════════════════════════════
  //  Init
  // ══════════════════════════════

  async function init() {
    try { allUsers = await api.getAdminUsers(); } catch { allUsers = []; }
    populateOverview();
    populateDetails();
    populateApprove();
    await loadCards();
  }

  init();
})();
