import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL });

// Attach JWT from localStorage to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, clear session and bounce to login.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !location.pathname.startsWith("/login")) {
      localStorage.removeItem("token");
      location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const API_BASE = baseURL;

// ── Auth ──────────────────────────────────────────────────────────────
export const authApi = {
  register: (email, password) => api.post("/auth/register", { email, password }),
  login: (email, password) => api.post("/auth/login", { email, password }),
  me: () => api.get("/auth/me"),
  gmailConnect: () => api.get("/auth/gmail/connect"),
};

// ── Profile ───────────────────────────────────────────────────────────
export const profileApi = {
  get: () => api.get("/profile/me"),
  update: (data) => api.put("/profile/me", data),
  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/profile/resume", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// ── Opportunities ─────────────────────────────────────────────────────
export const opportunitiesApi = {
  list: (params) => api.get("/opportunities", { params }),
  get: (id) => api.get(`/opportunities/${id}`),
  getEmail: (id) => api.get(`/opportunities/${id}/email`),
  create: (data) => api.post("/opportunities", data),
};

// ── Applications ──────────────────────────────────────────────────────
export const applicationsApi = {
  list: () => api.get("/applications"),
  create: (opportunity_id) => api.post("/applications", { opportunity_id }),
  updateStatus: (id, status) => api.put(`/applications/${id}/status`, { status }),
  remove: (id) => api.delete(`/applications/${id}`),
};

// ── AI ────────────────────────────────────────────────────────────────
export const aiApi = {
  extract: (subject, body) => api.post("/ai/extract", { subject, body }),
  optimizeResume: (oppId) => api.post(`/ai/resume/${oppId}`),
  tailorResume: (oppId) => api.post(`/ai/resume/${oppId}/tailor`),
  tailorLatex: (oppId) => api.post(`/ai/resume/${oppId}/tailor-latex`),
  coverLetter: (oppId) => api.post(`/ai/cover-letter/${oppId}`),
  research: (oppId) => api.get(`/ai/research/${oppId}`),
  recommend: () => api.get("/ai/recommend"),
};

// ── Analytics + Announcements ─────────────────────────────────────────
export const analyticsApi = {
  dashboard: () => api.get("/analytics/dashboard"),
  charts: (theme) => api.get("/analytics/charts", { params: { theme } }),
};

export const announcementsApi = {
  list: () => api.get("/announcements"),
};

export const gmailApi = {
  sync: () => api.post("/gmail/sync"),
};

export default api;
