import type { OllamaModel, OllamaStatus } from "../types/ollama";
import type { KaggleStatus } from "../types/kaggle";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: { method: "POST"; body: unknown }): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init ? {
    method: init.method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(init.body),
  } : undefined);
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
  getKaggleStatus: () => request<KaggleStatus>("/api/kaggle/status"),
  startKaggle: (model: string) => request<KaggleStatus>("/api/kaggle/start", { method: "POST", body: { model } }),
  setMode: (mode: "local" | "kaggle") => request<KaggleStatus>("/api/kaggle/mode", { method: "POST", body: { mode } }),
};
