import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  timeout: 60000,
});

const TOKEN_KEY = "dap_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token) {
  if (!token) localStorage.removeItem(TOKEN_KEY);
  else localStorage.setItem(TOKEN_KEY, token);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

function unwrap(res) {
  if (!res.data || res.data.ok !== true) {
    const msg = res.data?.error?.message || "请求失败";
    throw new Error(msg);
  }
  return res.data;
}

export async function authRegister(username, password) {
  const res = await api.post("/api/auth/register", { username, password });
  return unwrap(res);
}

export async function authLogin(username, password) {
  const res = await api.post("/api/auth/login", { username, password });
  return unwrap(res);
}

export async function authMe() {
  const res = await api.get("/api/auth/me");
  return unwrap(res);
}

export async function authLogout() {
  const res = await api.post("/api/auth/logout");
  return unwrap(res);
}

export async function uploadDataset(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post("/api/datasets/upload", form);
  return unwrap(res);
}

export async function cleanDataset(datasetId, opts) {
  const res = await api.post(`/api/datasets/${datasetId}/clean`, opts || {});
  return unwrap(res);
}

export async function trainDataset(datasetId, opts) {
  const res = await api.post(`/api/datasets/${datasetId}/train`, opts || {});
  return unwrap(res);
}

export async function exportDatasetUrl(datasetId) {
  return `${api.defaults.baseURL || ""}/api/datasets/${datasetId}/export`;
}

export async function downloadDatasetCsv(datasetId) {
  const res = await api.get(`/api/datasets/${datasetId}/export`, {
    responseType: "blob",
  });
  return res.data;
}

export async function stats(datasetId, params) {
  const res = await api.get(`/api/datasets/${datasetId}/stats`, { params });
  return unwrap(res);
}

export async function predict(modelRunId, rows, threshold) {
  const res = await api.post(`/api/model-runs/${modelRunId}/predict`, { rows, threshold });
  return unwrap(res);
}
