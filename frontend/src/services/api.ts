import type { OllamaModel, OllamaStatus } from "../types/ollama";
import type { KaggleNotebookSearchResponse, KaggleStatus } from "../types/kaggle";
import type { UIPreferences } from "../types/preferences";
import type { ProviderCatalog, ProviderPolicy } from "../types/providers";
import { request } from "./http";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const CATALOG_CACHE_MS = 15_000;
let providerCatalogCache: { value: ProviderCatalog; expiresAt: number } | null = null;
let providerCatalogPending: Promise<ProviderCatalog> | null = null;

async function getProviderCatalogCached(force = false): Promise<ProviderCatalog> {
  if (!force && providerCatalogCache && providerCatalogCache.expiresAt > Date.now()) {
    return providerCatalogCache.value;
  }
  if (!force && providerCatalogPending) return providerCatalogPending;
  const pending = request<ProviderCatalog>("/api/providers/catalog");
  providerCatalogPending = pending;
  try {
    const value = await pending;
    providerCatalogCache = { value, expiresAt: Date.now() + CATALOG_CACHE_MS };
    return value;
  } finally {
    if (providerCatalogPending === pending) providerCatalogPending = null;
  }
}

export const api = {
  getOllamaStatus: () => request<OllamaStatus>("/api/ollama/status"),
  getModels: () => request<OllamaModel[]>("/api/ollama/models"),
  getKaggleStatus: () => request<KaggleStatus>("/api/kaggle/status"),
  searchKaggleNotebooks: (query: string, page = 1) => request<KaggleNotebookSearchResponse>(`/api/kaggle/notebooks/search?q=${encodeURIComponent(query)}&page=${page}`),
  kaggleNotebookDownloadUrl: (ref: string) => `${API_BASE}/api/kaggle/notebooks/${ref.split("/").map(encodeURIComponent).join("/")}/download`,
  startKaggle: (model: string) => request<KaggleStatus>("/api/kaggle/start", { method: "POST", body: { model } }),
  setMode: (mode: "local" | "kaggle") => request<KaggleStatus>("/api/kaggle/mode", { method: "POST", body: { mode } }),
  getPreferences: () => request<UIPreferences>("/api/preferences"),
  savePreferences: (preferences: UIPreferences) => request<UIPreferences>("/api/preferences", { method: "PUT", body: preferences }),
  getProviderPolicy: () => request<ProviderPolicy>("/api/providers/policy"),
  saveProviderPolicy: (policy: ProviderPolicy) => request<ProviderPolicy>("/api/providers/policy", { method: "PUT", body: policy }),
  getProviderCatalog: () => getProviderCatalogCached(),
  refreshProviderCatalog: () => getProviderCatalogCached(true),
  invalidateProviderCatalog: () => { providerCatalogCache = null; providerCatalogPending = null; },
  getProviderDiagnostics: () => request<{ providers: { provider_id: string; connected: boolean | null; state: "available" | "cooldown" | "half_open"; cooldown_remaining_seconds: number; consecutive_failures: number; last_error_kind: string | null; last_error: string | null; last_success: boolean; recommendations: { code: string; level: "warning" | "error"; message: string }[] }[] }>("/api/diagnostics/providers"),
  setActiveProvider: async (provider_id: string) => {
    const result = await request<{ provider_id: string }>("/api/providers/active", { method: "PUT", body: { provider_id } });
    providerCatalogCache = null;
    return result;
  },
  getSecretStatus: () => request<Record<"kaggle-key" | "tunnel-password" | "openai-compatible-api-key", boolean>>("/api/secrets"),
  saveSecret: (name: string, value: string) => request<{ saved: boolean }>("/api/secrets", { method: "PUT", body: { name, value } }),
  deleteSecret: (name: string) => request<{ deleted: boolean }>(`/api/secrets/${encodeURIComponent(name)}`, { method: "DELETE" }),
};
