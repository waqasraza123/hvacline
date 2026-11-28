import { notifyExternalFailures } from "./external-failure-toast";
import { EXTERNAL_FAILURES_HEADER } from "./external-failures";

const MAX_NOTIFICATION_BODY_BYTES = 1_048_576;

async function notificationBody(response: Response): Promise<unknown> {
  if (
    !response.headers.get("content-type")?.includes("application/json") ||
    Number(response.headers.get("content-length") ?? 0) > MAX_NOTIFICATION_BODY_BYTES
  ) return undefined;
  const reader = response.clone().body?.getReader();
  if (!reader) return undefined;
  const decoder = new TextDecoder();
  let bytes = 0;
  let text = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return JSON.parse(text + decoder.decode());
      bytes += value.byteLength;
      if (bytes > MAX_NOTIFICATION_BODY_BYTES) {
        void reader.cancel().catch(() => undefined);
        return undefined;
      }
      text += decoder.decode(value, { stream: true });
    }
  } finally {
    reader.releaseLock();
  }
}

export async function providerFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (typeof window === "undefined") return response;
  let external: unknown;
  try {
    const header = response.headers.get(EXTERNAL_FAILURES_HEADER);
    if (header && header.length <= 4096) external = JSON.parse(header);
  } catch { external = undefined; }
  let body: unknown;
  try {
    body = await notificationBody(response);
  } catch { body = undefined; }
  try {
    notifyExternalFailures({ external_failures: external, details: body });
  } catch { /* A notification must not change the request outcome. */ }
  return response;
}
