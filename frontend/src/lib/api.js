export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const WS_BASE = import.meta.env.VITE_WS_BASE || "ws://localhost:8000";

export function clearAuthSession() {
  localStorage.removeItem("crime_user");
  localStorage.removeItem("crime_token");
}

export function authHeaders() {
  const token = localStorage.getItem("crime_token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function apiGet(path, params = {}) {
  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });
  const res = await fetch(url.toString(), { headers: { ...authHeaders() } });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : "Request failed");
  }
  return res.json();
}

export async function apiPost(path, body, isForm = false) {
  const init = {
    method: "POST",
    headers: isForm ? { ...authHeaders() } : { ...authHeaders(), "Content-Type": "application/json" },
    body: isForm ? body : JSON.stringify(body)
  };
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = data.detail;
    throw new Error(
      typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : data.message || "Request failed"
    );
  }
  return res.json();
}

export async function apiUpload(path, file, fieldName = "file") {
  const fd = new FormData();
  fd.append(fieldName, file);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: fd
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.message || "Upload failed");
  }
  return res.json();
}

export async function apiPatch(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.message || "Request failed");
  }
  return res.json();
}
