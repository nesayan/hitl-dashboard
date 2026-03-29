(function () {
  // Guard: redirect to login if not authenticated as user
  const role = sessionStorage.getItem("role");
  const username = sessionStorage.getItem("username");
  const userId = sessionStorage.getItem("user_id");
  if (role !== "user" || !username || !userId) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("navUser").textContent = `Logged in as: ${username}`;
  document.getElementById("logoutBtn").addEventListener("click", () => {
    sessionStorage.clear();
    window.location.href = "index.html";
  });

  const tbody = document.getElementById("tasksBody");
  const statusFilter = document.getElementById("statusFilter");
  const refreshBtn = document.getElementById("refreshBtn");

  let allTasks = [];

  const STATUS_BADGES = {
    pending: "bg-warning text-dark",
    approved: "bg-success",
    rejected: "bg-danger",
    cancelled: "bg-secondary",
    completed: "bg-info text-dark",
  };

  function formatDate(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    return d.toLocaleString();
  }

  function truncate(text, len = 40) {
    if (!text) return "-";
    const s = typeof text === "object" ? JSON.stringify(text) : String(text);
    return s.length > len ? s.substring(0, len) + "..." : s;
  }

  function renderTasks(tasks) {
    if (tasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">No tasks found.</td></tr>`;
      return;
    }

    tbody.innerHTML = tasks
      .map((t) => {
        const badgeClass = STATUS_BADGES[t.status] || "bg-secondary";
        const canCancel = t.status === "pending";

        return `
        <tr>
          <td title="${t.hitl_task_id}">${truncate(t.hitl_task_id, 12)}</td>
          <td>${t.task_name || "-"}</td>
          <td title="${t.task_description || ""}">${truncate(t.task_description, 30)}</td>
          <td class="task-args" title='${t.task_args ? JSON.stringify(t.task_args) : "-"}'>${truncate(t.task_args, 25)}</td>
          <td><span class="badge ${badgeClass}">${t.status}</span></td>
          <td title="${t.output || ""}">${truncate(t.output, 30)}</td>
          <td>${formatDate(t.created_at)}</td>
          <td>${formatDate(t.updated_at)}</td>
          <td>
            ${canCancel
              ? `<button class="btn btn-sm btn-outline-danger cancel-btn" data-id="${t.hitl_task_id}">Cancel</button>`
              : `<span class="text-muted">-</span>`
            }
          </td>
        </tr>`;
      })
      .join("");

    // Attach cancel handlers
    document.querySelectorAll(".cancel-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const taskId = btn.dataset.id;
        btn.disabled = true;
        btn.textContent = "...";

        try {
          await api.updateHITLTask(taskId, { status: "cancelled" });
          showToast("Task cancelled successfully.", "bg-success");
          await loadTasks();
        } catch (err) {
          showToast("Failed to cancel: " + err.message, "bg-danger");
        } finally {
          btn.disabled = false;
          btn.textContent = "Cancel";
        }
      });
    });
  }

  async function loadTasks() {
    try {
      allTasks = await api.getHITLTasksByUser(userId);
      applyFilter();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load tasks.</td></tr>`;
    }
  }

  function applyFilter() {
    const filter = statusFilter.value;
    const filtered = filter ? allTasks.filter((t) => t.status === filter) : allTasks;
    renderTasks(filtered);
  }

  statusFilter.addEventListener("change", applyFilter);
  refreshBtn.addEventListener("click", loadTasks);

  function showToast(message, bgClass) {
    const toastEl = document.getElementById("toast");
    const toastBody = document.getElementById("toastBody");
    toastEl.className = `toast align-items-center border-0 text-white ${bgClass}`;
    toastBody.textContent = message;
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
  }

  // Initial load
  loadTasks();
})();
