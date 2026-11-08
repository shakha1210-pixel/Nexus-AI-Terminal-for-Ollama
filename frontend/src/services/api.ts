import type { KaggleNotebook, KagglePullResponse } from "../types/kaggle";
import type { OllamaModel, OllamaStatus } from "../types/ollama";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `API xatosi: ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Javob JSON bo‘lmasa, standart xabar ishlatiladi.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getOllamaStatus: () => request<OllamaStatus>("/api/ollama/status"),
  getModels: () => request<OllamaModel[]>("/api/ollama/models"),
  getKaggleNotebooks: (search?: string, page = 1) => {
    const params = new URLSearchParams({ page: String(page) });
    if (search?.trim()) params.set("search", search.trim());
    return request<KaggleNotebook[]>(`/api/kaggle/notebooks?${params.toString()}`);
  },
  pullKaggleNotebook: (owner: string, slug: string) =>
    request<KagglePullResponse>(
      `/api/kaggle/notebooks/${encodeURIComponent(owner)}/${encodeURIComponent(slug)}/pull`,
      { method: "POST" },
    ),
};
