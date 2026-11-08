export interface KaggleNotebook {
  ref: string;
  title: string;
  language: string | null;
  votes: number;
  last_updated: string | null;
  url: string;
  is_pulled: boolean;
}

export interface KagglePullResponse {
  ref: string;
  filename: string;
  status: "downloaded" | string;
}
