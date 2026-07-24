const BASE = "http://localhost:8000";

// One function every screen uses to talk to the backend.
// It auto-adds the API address and your login token.
export async function api(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = { ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;  

  const res = await fetch(BASE + path, { ...options, headers });
  if (res.status === 401) {                 // token expired/invalid
    localStorage.removeItem("token");
    window.location.reload();               // kick back to login
  }
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}
