/**
 * Centralized API & WebSocket client for CrimeWatch AI Platform.
 * Supports VITE_API_URL and VITE_WS_URL with legacy fallbacks.
 */

// Normalized API base URL (defaults to localhost:8000 for development)
const rawApiUrl =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE ||
  "http://localhost:8000";

export const API_BASE = rawApiUrl.replace(/\/+$/, "");
export const API_URL = API_BASE;

// Normalized WebSocket base URL
function resolveWsBase() {
  const customWs = import.meta.env.VITE_WS_URL || import.meta.env.VITE_WS_BASE;
  if (customWs) {
    return customWs.replace(/\/+$/, "");
  }
  if (API_BASE.startsWith("https://")) {
    return API_BASE.replace(/^https:\/\//, "wss://");
  }
  return API_BASE.replace(/^http:\/\//, "ws://");
}

export const WS_BASE = resolveWsBase();
export const WS_URL = WS_BASE;

// Local session helpers
export function getStoredToken() {
  return localStorage.getItem("crime_token") || "";
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem("crime_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  localStorage.removeItem("crime_user");
  localStorage.removeItem("crime_token");
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("crime:auth_cleared"));
  }
}

export function authHeaders() {
  const token = getStoredToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * Handle HTTP error responses consistently without leaking internals
 */
async function parseError(res) {
  let body = {};
  try {
    body = await res.json();
  } catch {
    // Response not JSON
  }

  if (res.status === 401) {
    clearAuthSession();
  }

  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(", ");
  }
  return body.message || `Request failed with status ${res.status}`;
}

/**
 * GET request with query params and authorization
 */
export async function apiGet(path, params = {}) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE}${cleanPath}`);
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  const res = await fetch(url.toString(), {
    headers: { ...authHeaders() },
  });

  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * POST request with JSON or FormData payload
 */
export async function apiPost(path, body, isForm = false) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const init = {
    method: "POST",
    headers: isForm ? { ...authHeaders() } : { ...authHeaders(), "Content-Type": "application/json" },
    body: isForm ? body : JSON.stringify(body),
  };

  const res = await fetch(`${API_BASE}${cleanPath}`, init);
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * PUT request with JSON or FormData payload
 */
export async function apiPut(path, body, isForm = false) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const init = {
    method: "PUT",
    headers: isForm ? { ...authHeaders() } : { ...authHeaders(), "Content-Type": "application/json" },
    body: isForm ? body : JSON.stringify(body),
  };

  const res = await fetch(`${API_BASE}${cleanPath}`, init);
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * PATCH request with JSON or FormData payload
 */
export async function apiPatch(path, body, isForm = false) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const init = {
    method: "PATCH",
    headers: isForm ? { ...authHeaders() } : { ...authHeaders(), "Content-Type": "application/json" },
    body: isForm ? body : JSON.stringify(body),
  };

  const res = await fetch(`${API_BASE}${cleanPath}`, init);
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * DELETE request
 */
export async function apiDelete(path) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${API_BASE}${cleanPath}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * File upload helper supporting single File or FormData
 */
export async function apiUpload(path, fileOrFormData, fieldName = "file") {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  let fd;
  if (fileOrFormData instanceof FormData) {
    fd = fileOrFormData;
  } else {
    fd = new FormData();
    fd.append(fieldName, fileOrFormData);
  }

  const res = await fetch(`${API_BASE}${cleanPath}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: fd,
  });

  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * Binary blob download helper (for audio/image evidence)
 */
export async function apiFetchBlob(path) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${API_BASE}${cleanPath}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.blob();
}

export default {
  API_BASE,
  API_URL,
  WS_BASE,
  WS_URL,
  getStoredToken,
  getStoredUser,
  clearAuthSession,
  authHeaders,
  apiGet,
  apiPost,
  apiPut,
  apiPatch,
  apiDelete,
  apiUpload,
  apiFetchBlob,
};
