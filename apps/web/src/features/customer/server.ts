import { cookies } from "next/headers";

export type Customer = Readonly<{
  id: string;
  full_name: string;
  email: string;
}>;
export const CUSTOMER_COOKIE =
  process.env.NODE_ENV === "production"
    ? "__Host-hvacline-session"
    : "hvacline-session";

export class CustomerBackendError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "CustomerBackendError";
  }
}

export function parseCustomer(value: unknown): Customer {
  if (
    typeof value !== "object" ||
    value === null ||
    !("id" in value) ||
    !("full_name" in value) ||
    !("email" in value) ||
    typeof value.id !== "string" ||
    typeof value.full_name !== "string" ||
    typeof value.email !== "string"
  ) {
    throw new CustomerBackendError(
      502,
      "Your account could not be loaded. Please try again.",
    );
  }
  return { id: value.id, full_name: value.full_name, email: value.email };
}

export async function customerBackend(
  path: string,
  method = "GET",
  body?: string,
  idempotencyKey?: string,
): Promise<Response> {
  const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  const secret = process.env.CUSTOMER_PORTAL_SECRET;
  if (!rawBase || !secret || secret.length < 32)
    throw new CustomerBackendError(
      503,
      "Customer booking is not available yet. Please try again later.",
    );
  const base = new URL(rawBase);
  if (process.env.NODE_ENV === "production" && base.protocol !== "https:") throw new CustomerBackendError(503, "Customer booking is temporarily unavailable.");
  if (
    !["http:", "https:"].includes(base.protocol) ||
    base.username ||
    base.password ||
    base.search ||
    base.hash
  )
    throw new CustomerBackendError(
      503,
      "Customer booking is temporarily unavailable.",
    );
  const token = (await cookies()).get(CUSTOMER_COOKIE)?.value;
  return fetch(
    `${base.toString().replace(/\/$/, "")}/api/v1/customer/${path}`,
    {
      method,
      body,
      cache: "no-store",
      redirect: "error",
      headers: {
        "Content-Type": "application/json",
        "X-Customer-Portal-Key": secret,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
      },
      signal: AbortSignal.timeout(20_000),
    },
  );
}

export async function currentCustomer(): Promise<
  | { status: "authenticated"; user: Customer }
  | { status: "anonymous" | "unavailable" }
> {
  if (!(await cookies()).has(CUSTOMER_COOKIE)) return { status: "anonymous" };
  try {
    const response = await customerBackend("auth/me");
    if (response.status === 401) return { status: "anonymous" };
    if (!response.ok) return { status: "unavailable" };
    return {
      status: "authenticated",
      user: parseCustomer(await response.json()),
    };
  } catch {
    return { status: "unavailable" };
  }
}
