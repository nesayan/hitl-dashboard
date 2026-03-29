document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const errorEl = document.getElementById("loginError");
  errorEl.classList.add("d-none");

  if (!username) return;

  try {
    const user = await api.getUserByUsername(username);

    if (!user) {
      errorEl.textContent = "User not found. Please check the username.";
      errorEl.classList.remove("d-none");
      return;
    }

    sessionStorage.setItem("user_id", user.user_id);
    sessionStorage.setItem("username", user.username);

    if (user.username.toLowerCase() === "admin") {
      sessionStorage.setItem("role", "admin");
      window.location.href = "admin.html";
    } else {
      sessionStorage.setItem("role", "user");
      window.location.href = "user.html";
    }
  } catch (err) {
    errorEl.textContent = "Unable to connect to server. Is the backend running?";
    errorEl.classList.remove("d-none");
  }
});
