export type SwitchingMode = "disabled" | "manual_only" | "error_triggered" | "exception_based" | "guided";
export type FailureKind = "timeout" | "rate_limit" | "server_error" | "network_error" | "authentication" | "model_not_found" | "user_cancelled" | "security_block" | "unknown";
export interface ProviderPolicy {
  mode: SwitchingMode;
  max_switches_per_request: number;
  allowed_transitions: Record<string, string[]>;
  exception_allowlist: FailureKind[];
  retry_limit: number;
  cooldown_seconds: number;
  require_confirmation: boolean;
  updated?: boolean;
}
export interface ProviderModelInfo {
  name: string;
  display_name: string;
  capabilities: { streaming: boolean; tool_calling: boolean; vision: boolean; embeddings: boolean; json_mode: boolean };
  metadata: Record<string, unknown>;
}
export interface ProviderInfo {
  id: string;
  name: string;
  configured: boolean;
  connected: boolean;
  models: ProviderModelInfo[];
}
export interface ProviderCatalog {
  active_provider: string;
  providers: ProviderInfo[];
}
