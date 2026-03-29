(function () {
  const role = sessionStorage.getItem("role");
  const username = sessionStorage.getItem("username");
  const userId = sessionStorage.getItem("user_id");
  if (role !== "user" || !username || !userId) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("navUser").textContent = "Logged in as: " + username;
  document.getElementById("logoutBtn").addEventListener("click", function () {
    sessionStorage.clear();
    window.location.href = "index.html";
  });

  var STATUS_BADGES = {
    pending: "bg-warning text-dark",
    approved: "bg-success",
    rejected: "bg-danger",
    cancelled: "bg-secondary",
    completed: "bg-info text-dark",
  };

  var tbody = document.getElementById("tasksBody");
  var statusFilter = document.getElementById("statusFilter");
  var refreshBtn = document.getElementById("refreshBtn");
  var allTasks = [];

  function formatDate(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleString();
  }

  function truncate(text, len) {
    len = len || 40;
    if (!text) return "-";
    var s = typeof text === "object" ? JSON.stringify(text) : String(text);
    return s.length > len ? s.substring(0, len) + "..." : s;
  }

  function showToast(message, bgClass) {
    var toastEl = document.getElementById("toast");
    var toastBody = document.getElementById("toastBody");
    toastEl.className = "toast align-items-center border-0 text-white " + bgClass;
    toastBody.textContent = message;
    new bootstrap.Toast(toastEl, { delay: 3000 }).show();
  }

  function renderTasks(tasks) {
    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No tasks found.</td></tr>';
      return;
    }
    var html = "";
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      var badge = STATUS_BADGES[t.status] || "bg-secondary";
      var canCancel = t.status === "pending";
      html += "<tr>";
      html += "<td>" + (t.task_name || "-") + "</td>";
      html += '<td title="' + (t.task_description || "") + '">' + truncate(t.task_description, 30) + "</td>";
      html += '<td class="task-args">' + truncate(t.task_args, 25) + "</td>";
      html += '<td><span class="badge ' + badge + '">' + t.status + "</span></td>";
      html += '<td title="' + (t.output || "") + '">' + truncate(t.output, 30) + "</td>";
      html += "<td>" + formatDate(t.created_at) + "</td>";
      html += "<td>" + formatDate(t.updated_at) + "</td>";
      if (canCancel) {
        html += '<td><button class="btn btn-sm btn-outline-danger cancel-btn" data-id="' + t.hitl_task_id + '"><i class="bi bi-x-circle"></i> Cancel</button></td>';
      } else {
        html += '<td><span class="text-muted">-</span></td>';
      }
      html += "</tr>";
    }
    tbody.innerHTML = html;

    var cancelBtns = document.querySelectorAll(".cancel-btn");
    for (var j = 0; j < cancelBtns.length; j++) {
      cancelBtns[j].addEventListener("click", handleCancel);
    }
  }

  function handleCancel(e) {
    var btn = e.currentTarget;
    var taskId = btn.getAttribute("data-id");
    btn.disabled = true;
    api.updateHITLTask(taskId, { status: "cancelled" })
      .then(function () {
        showToast("Task cancelled.", "bg-success");
        loadTasks();
      })
      .catch(function (err) {
        showToast("Failed to cancel: " + err.message, "bg-danger");
        btn.disabled = false;
      });
  }

  function loadTasks() {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Loading...</td></tr>';
    api.getHITLTasksByUser(userId)
      .then(function (tasks) {
        allTasks = tasks;
        applyFilter();
      })
      .catch(function () {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Failed to load tasks.</td></tr>';
      });
  }

  function applyFilter() {
    var f = statusFilter.value;
    if (f) {
      var filtered = [];
      for (var i = 0; i < allTasks.length; i++) {
        if (allTasks[i].status === f) filtered.push(allTasks[i]);
      }
      renderTasks(filtered);
    } else {
      renderTasks(allTasks);
    }
  }

  statusFilter.addEventListener("change", applyFilter);
  refreshBtn.addEventListener("click", loadTasks);

  loadTasks();

  /* ════════════════════════════════════════
     Chat Tab
     ════════════════════════════════════════ */
  var chatMessages = document.getElementById("chatMessages");
  var chatForm = document.getElementById("chatForm");
  var chatInput = document.getElementById("chatInput");
  var sendBtn = document.getElementById("sendBtn");
  var emptyState = document.getElementById("emptyState");

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideEmptyState() {
    if (emptyState) emptyState.style.display = "none";
  }

  function addBubble(text, sender) {
    hideEmptyState();
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble chat-" + sender;
    bubble.textContent = text;
    var row = document.createElement("div");
    row.className = "chat-row chat-row-" + sender;
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function addThinking() {
    hideEmptyState();
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble chat-bot thinking";
    bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    var row = document.createElement("div");
    row.className = "chat-row chat-row-bot";
    row.id = "thinkingRow";
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function removeThinking() {
    var el = document.getElementById("thinkingRow");
    if (el) el.remove();
  }

  function setChatEnabled(on) {
    chatInput.disabled = !on;
    sendBtn.disabled = !on;
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var message = chatInput.value.trim();
    if (!message) return;

    addBubble(message, "user");
    chatInput.value = "";
    setChatEnabled(false);
    addThinking();

    api.queryAgent(userId, message)
      .then(function (data) {
        removeThinking();
        addBubble(data.response || "No response.", "bot");
      })
      .catch(function (err) {
        removeThinking();
        addBubble("Error: " + err.message, "bot");
        showToast("Failed to send message: " + err.message, "bg-danger");
      })
      .finally(function () {
        setChatEnabled(true);
        chatInput.focus();
      });
  });
})();
