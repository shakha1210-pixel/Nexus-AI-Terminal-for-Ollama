export type KaggleState = "idle" | "pushing" | "queued" | "starting" | "online" | "stopped" | "error";

export interface KaggleStatus {
  state: KaggleState;
  model: string | null;
  kernel: string | null;
  endpoint: string | null;
  openai_base_url: string | null;
  mode: "local" | "kaggle";
  message: string;
}
