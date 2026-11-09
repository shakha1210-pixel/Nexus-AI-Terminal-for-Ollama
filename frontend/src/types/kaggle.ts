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


export interface KaggleNotebookItem {
  ref: string;
  title: string;
  author: string;
  last_run: string;
  votes: number;
}

export interface KaggleNotebookSearchResponse {
  query: string;
  page: number;
  items: KaggleNotebookItem[];
}
