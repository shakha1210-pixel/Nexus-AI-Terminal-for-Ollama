import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { OllamaModel, OllamaStatus } from "../types/ollama";
import type { KaggleStatus } from "../types/kaggle";

type RuntimeProviderModel = {
  name: string;
  metadata: Record<string, unknown>;
};

function toOllamaModel(item: RuntimeProviderModel): OllamaModel {
  return {
    name: item.name,
    size: typeof item.metadata.size === "number" ? item.metadata.size : null,
    modified_at: typeof item.metadata.modified_at === "string" ? item.metadata.modified_at : null,
    digest: typeof item.metadata.digest === "string" ? item.metadata.digest : null,
    family: typeof item.metadata.family === "string" ? item.metadata.family : null,
    parameter_size: typeof item.metadata.parameter_size === "string" ? item.metadata.parameter_size : null,
    quantization_level: typeof item.metadata.quantization_level === "string" ? item.metadata.quantization_level : null,
  };
}

export function useRuntimeStatus() {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [kaggleStatus, setKaggleStatus] = useState<KaggleStatus | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [providerModels, setProviderModels] = useState<OllamaModel[]>([]);
  const [activeProvider, setActiveProvider] = useState("ollama");
  const [providerConnected, setProviderConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const refreshing = useRef(false);

  const refresh = useCallback(async (silent = false) => {
    if (refreshing.current) return;
    refreshing.current = true;
    if (!silent) setLoading(true);
    setError(null);

    try {
      const [nextStatus, nextKaggleStatus, catalog] = await Promise.all([
        api.getOllamaStatus().catch(() => null),
        api.getKaggleStatus().catch(() => null),
        api.getProviderCatalog().catch(() => null),
      ]);

      if (nextStatus) {
        setStatus(nextStatus);
        if (nextStatus.connected) {
          setModels(await api.getModels().catch(() => []));
        } else {
          setModels([]);
        }
      } else {
        setStatus({ connected: false, version: null, mode: "local", message: "Backend API is unavailable." });
        setModels([]);
      }

      if (nextKaggleStatus) setKaggleStatus(nextKaggleStatus);
      if (catalog) {
        setActiveProvider(catalog.active_provider);
        const selected = catalog.providers.find((provider) => provider.id === catalog.active_provider);
        setProviderConnected(Boolean(selected?.connected));
        setProviderModels((selected?.models ?? []).map((item) => toOllamaModel(item)));
      } else {
        setProviderConnected(false);
        setProviderModels([]);
      }

      if (!nextStatus && !nextKaggleStatus && !catalog) {
        setError("Unable to retrieve runtime status.");
      }
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected runtime error occurred.");
      setStatus({ connected: false, version: null, mode: "local", message: "Backend API is unavailable." });
      setModels([]);
      setProviderModels([]);
      setProviderConnected(false);
    } finally {
      refreshing.current = false;
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh(true);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return {
    status, kaggleStatus, setKaggleStatus, models, providerModels,
    activeProvider, setActiveProvider, providerConnected, loading,
    error, setError, updatedAt, refresh,
  };
}
