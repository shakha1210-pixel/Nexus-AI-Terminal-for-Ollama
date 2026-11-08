import type { OllamaModel, OllamaStatus } from "../types/ollama";
import type { KaggleStatus } from "../types/kaggle";
import type { UIPreferences } from "../types/preferences";
import type { ProviderCatalog, ProviderPolicy } from "../types/providers";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: { method: "POST" | "PUT" | "DELETE"; body?: unknown }): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init ? {
    method: init.method,
    headers: { "Content-Type": "application/json" },
    ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
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
  getPreferences: () => request<UIPreferences>("/api/preferences"),
  savePreferences: (preferences: UIPreferences) => request<UIPreferences>("/api/preferences", { method: "PUT", body: preferences }),
  getProviderPolicy: () => request<ProviderPolicy>("/api/providers/policy"),
  saveProviderPolicy: (policy: ProviderPolicy) => request<ProviderPolicy>("/api/providers/policy", { method: "PUT", body: policy }),
  getProviderCatalog: () => request<ProviderCatalog>("/api/providers/catalog"),
  setActiveProvider: (provider_id: string) => request<{ provider_id: string }>("/api/providers/active", { method: "PUT", body: { provider_id } }),
  getSecretStatus: () => request<Record<"kaggle-key" | "tunnel-password" | "openai-compatible-api-key", boolean>>("/api/secrets"),
  saveSecret: (name: string, value: string) => request<{ saved: boolean }>("/api/secrets", { method: "PUT", body: { name, value } }),
  deleteSecret: (name: string) => request<{ deleted: boolean }>(`/api/secrets/${encodeURIComponent(name)}`, { method: "DELETE" }),
};
