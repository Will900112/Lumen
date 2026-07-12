const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Token storage
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

// Shared fetch wrapper
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 || res.status === 403) {
    clearToken();
    window.location.href = "/login?expired=1";
    throw new Error("Session expired");
  }


  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    // detail can be a plain string or an object like {step, message}
    const detail = error.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || `HTTP ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

// Auth
export async function register(email: string, password: string) {
  return request<{ id: string; email: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_BASE}/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

// JWT is stateless — the server has nothing to revoke, so logout is local only.
export function logout() {
  clearToken();
}

export async function googleAuthorize() {
  const res = await fetch(`${API_BASE}/auth/google/authorize`);
  if (!res.ok) throw new Error("Failed to get Google authorize URL");
  const data = await res.json();
  return data.authorization_url as string;
}

// Pipeline
export async function recommend(questionnaire: Record<string, unknown>) {
  return request<{
    session_id: string;
    gap_pack: unknown[];
    symptom_pack: unknown[];
    goal_pack: unknown[];
    safety_warnings: string[];
    narrative: string;
  }>("/recommend", {
    method: "POST",
    body: JSON.stringify({ questionnaire }),
  });
}

export async function chat(sessionId: string, message: string) {
  return request<{ reply: string }>("/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

// Sessions
export async function listSessions() {
  return request<Array<{ id: string; created_at: string; narrative: string }>>(
    "/sessions"
  );
}

export async function getSession(id: string) {
  return request<{
    id: string;
    created_at: string;
    gap_pack: unknown[];
    symptom_pack: unknown[];
    goal_pack: unknown[];
    safety_warnings: string[];
    narrative: string;
    messages: Array<{ role: string; content: string; created_at: string }>;
  }>(`/sessions/${id}`);
}

// Saved supplements
export async function saveSupplement(sessionId: string, name: string) {
  return request<{ id: string; name: string }>("/list/add", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, name }),
  });
}

export async function listSaved() {
  return request<
    Array<{ id: string; name: string; session_id: string; created_at: string }>
  >("/list");
}

export async function deleteSaved(id: string) {
  return request<{ ok: boolean }>(`/list/${id}`, { method: "DELETE" });
}
