import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  timeout: 60000,
});

function unwrap(res) {
  if (!res.data || res.data.ok !== true) {
    const msg = res.data?.error?.message || "请求失败";
    throw new Error(msg);
  }
  return res.data;
}

export async function uploadDataset(file, targetCol = "depression_label") {
  const form = new FormData();
  form.append("file", file);
  form.append("target_col", targetCol);
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

export async function stats(datasetId, params) {
  const res = await api.get(`/api/datasets/${datasetId}/stats`, { params });
  return unwrap(res);
}

export async function predict(modelRunId, rows, threshold) {
  const res = await api.post(`/api/model-runs/${modelRunId}/predict`, { rows, threshold });
  return unwrap(res);
}

