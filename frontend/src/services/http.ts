const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export type ServerSentEvent = {
  event: string;
  data: string;
  id?: string;
  retry?: number;
};

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `API xatosi: ${response.status}`;
    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // Preserve the status-based fallback for non-JSON error responses.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function openEventStream(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `API xatosi: ${response.status}`;
    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  if (!response.body) throw new Error("Streaming javob mavjud emas.");
  return response;
}

function parseEventBlock(block: string): ServerSentEvent | null {
  let event = "message";
  let data = "";
  let id: string | undefined;
  let retry: number | undefined;
  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    const separator = line.indexOf(":");
    const field = separator < 0 ? line : line.slice(0, separator);
    let value = separator < 0 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data += (data ? "\n" : "") + value;
    else if (field === "id" && !value.includes("\0")) id = value;
    else if (field === "retry" && /^\d+$/.test(value)) retry = Number(value);
  }
  return data || event !== "message" || id !== undefined || retry !== undefined
    ? { event, data, id, retry }
    : null;
}

export async function readEventStream(
  response: Response,
  onEvent: (event: ServerSentEvent) => void | Promise<void>,
  signal?: AbortSignal,
): Promise<void> {
  if (!response.body) throw new Error("Streaming javob mavjud emas.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const dispatch = async (block: string) => {
    const event = parseEventBlock(block);
    if (event) await onEvent(event);
  };
  const cancel = () => { void reader.cancel(signal?.reason).catch(() => undefined); };
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    while (true) {
      if (signal?.aborted) break;
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.search(/\r?\n\r?\n/);
      while (boundary >= 0) {
        const delimiter = buffer.slice(boundary).match(/^\r?\n\r?\n/)?.[0] ?? "\n\n";
        await dispatch(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + delimiter.length);
        boundary = buffer.search(/\r?\n\r?\n/);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) await dispatch(buffer);
  } finally {
    signal?.removeEventListener("abort", cancel);
    reader.releaseLock();
  }
}
