import { record } from "./models";

export function webOrigin(): string {
  const raw = process.env.EXPO_PUBLIC_WEB_ORIGIN;
  if (!raw)
    throw new Error(
      "Set EXPO_PUBLIC_WEB_ORIGIN to your configured HVACLine website before opening the app.",
    );
  const url = new URL(raw);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error(
      "EXPO_PUBLIC_WEB_ORIGIN must be a public HTTPS origin without a path.",
    );
  return url.origin;
}

export class MobileApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
  }
}

export class MobileApi {
  constructor(
    readonly origin: string,
    private readonly token?: string,
    private readonly onUnauthorized?: () => void,
  ) {}

  async request<T = unknown>(
    path: string,
    method: "GET" | "POST" = "GET",
    body?: unknown,
    key?: string,
  ): Promise<T> {
    if (
      !/^[a-zA-Z0-9/-]+$/.test(path) ||
      path.startsWith("/") ||
      path.includes("//")
    )
      throw new Error("Invalid mobile API action.");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 25_000);
    try {
      const response = await fetch(`${this.origin}/api/mobile/${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
          ...(key ? { "Idempotency-Key": key } : {}),
        },
        body: method === "POST" ? JSON.stringify(body ?? {}) : undefined,
        signal: controller.signal,
        credentials: "omit",
        redirect: "error",
      });
      if (response.status === 204) return undefined as T;
      const data: unknown = await response.json().catch(() => undefined);
      if (!response.ok) {
        if (response.status === 401) this.onUnauthorized?.();
        const error =
          record(data) && record(data.error) ? data.error : undefined;
        throw new MobileApiError(
          response.status,
          typeof error?.message === "string"
            ? error.message
            : "The request could not be completed. Please try again.",
          typeof error?.code === "string" ? error.code : undefined,
          record(error?.details) ? error.details : undefined,
        );
      }
      if (data === undefined)
        throw new MobileApiError(
          502,
          "The service returned an unreadable response.",
        );
      return data as T;
    } catch (error) {
      if (error instanceof MobileApiError) throw error;
      throw new MobileApiError(
        0,
        "Could not establish the result. Check your connection and retry the same action.",
      );
    } finally {
      clearTimeout(timeout);
    }
  }
}
