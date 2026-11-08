export interface OllamaStatus {
  connected: boolean;
  version: string | null;
  mode: "local" | "kaggle";
  message: string;
}

export interface OllamaModel {
  name: string;
  size: number | null;
  modified_at: string | null;
  digest: string | null;
  family: string | null;
  parameter_size: string | null;
  quantization_level: string | null;
}
