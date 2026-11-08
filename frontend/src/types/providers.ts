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
