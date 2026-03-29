// API_BASE is set by /env.js loaded before this script

const api = {
  async getUsers() {
    const res = await fetch(`${API_BASE}/users/`);
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  async getUserByUsername(username) {
    const res = await fetch(`${API_BASE}/users/by-username?username=${encodeURIComponent(username)}`);
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error("Failed to fetch user");
    }
    return res.json();
  },

  async getAllHITLTasks() {
    const res = await fetch(`${API_BASE}/hitl/`);
    if (!res.ok) throw new Error("Failed to fetch HITL tasks");
    return res.json();
  },

  async getAdminUsers() {
    const res = await fetch(`${API_BASE}/users/`);
    if (!res.ok) throw new Error("Failed to fetch users");
    return res.json();
  },

  async getUserRunsByUser(userId) {
    const res = await fetch(`${API_BASE}/user-runs/by-user?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error("Failed to fetch user runs");
    return res.json();
  },

  async getHITLTasksByUser(userId, status = null) {
    let url = `${API_BASE}/hitl/user?user_id=${encodeURIComponent(userId)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch user HITL tasks");
    return res.json();
  },

  async updateHITLTask(taskId, data) {
    const res = await fetch(`${API_BASE}/hitl/${encodeURIComponent(taskId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update task");
    }
    return res.json();
  },

  async approveTask(hitlTaskId, userId, userRunId) {
    const res = await fetch(`${API_BASE}/admin/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hitl_task_id: hitlTaskId, user_id: userId, user_run_id: userRunId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to approve task");
    }
    return res.json();
  },

  async rejectTask(hitlTaskId) {
    const res = await fetch(`${API_BASE}/admin/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hitl_task_id: hitlTaskId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to reject task");
    }
    return res.json();
  },

  async queryAgent(userId, message) {
    const res = await fetch(`${API_BASE}/agent/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, message }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to query agent");
    }
    return res.json();
  },
};
