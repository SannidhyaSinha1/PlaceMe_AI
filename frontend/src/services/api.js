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

// ── Opportunities (company details parsed out of each email) ──────────
export const opportunitiesApi = {
  list: (params, signal) => api.get("/opportunities", { params, signal }),
  get: (id) => api.get(`/opportunities/${id}`),
  getEmail: (id) => api.get(`/opportunities/${id}/email`),
};

// ── Gmail ─────────────────────────────────────────────────────────────
export const gmailApi = {
  sync: () => api.post("/gmail/sync"),
};

export default api;
