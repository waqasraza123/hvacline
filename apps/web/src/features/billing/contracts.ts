import defaults from "../../../../backend/src/insurance_operations/billing/plans.json";

export type PlanKey = "essential" | "comfort" | "complete";
export type Plan = {
  key: PlanKey;
  name: string;
  amount: number;
  included_hours: number;
  hourly_amount: number;
  description: string;
};
export type Catalog = {
  plans: Plan[];
  checkout_enabled: boolean;
  draft: boolean;
};
export const draftCatalog: Catalog = {
  plans: defaults as Plan[],
  checkout_enabled: false,
  draft: true,
};
export type Billing = {
  plan: PlanKey | "none";
  subscription_status: string;
  period_start: string | null;
  period_end: string | null;
  cancel_at_period_end: boolean;
  checkout_enabled: boolean;
  portal_enabled: boolean;
  sync_pending: boolean;
  checkout_pending: boolean;
  pending_checkout_id: string | null;
  review_required: boolean;
  included_minutes: number;
  used_package_minutes: number;
  remaining_package_minutes: number;
  purchased_minutes: number;
  used_purchased_minutes: number;
  remaining_purchased_minutes: number;
  hourly_amount: number | null;
  last_synced_at: string | null;
};
export type TopUp = {
  id: string;
  plan: PlanKey;
  minutes: number;
  hourly_amount: number;
  amount: number;
  status: "creating" | "open" | "paid" | "expired";
  created_at: string;
  credited_at: string | null;
};
export type Labor = {
  id: string;
  appointment_id: string;
  minutes: number;
  package_minutes: number;
  purchased_minutes: number;
  created_at: string;
};
export type History = { topups: TopUp[]; labor: Labor[] };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseCatalog(value: unknown): Catalog {
  if (
    !isRecord(value) ||
    !Array.isArray(value.plans) ||
    value.plans.length !== 3 ||
    typeof value.checkout_enabled !== "boolean" ||
    typeof value.draft !== "boolean"
  ) {
    throw new Error("Package pricing could not be loaded. Please refresh.");
  }
  const keys = new Set<string>();
  for (const plan of value.plans) {
    if (
      !isRecord(plan) ||
      typeof plan.key !== "string" ||
      !["essential", "comfort", "complete"].includes(plan.key) ||
      keys.has(plan.key) ||
      typeof plan.name !== "string" ||
      typeof plan.description !== "string" ||
      ![plan.amount, plan.included_hours, plan.hourly_amount].every(
        (amount) =>
          typeof amount === "number" && Number.isInteger(amount) && amount > 0,
      )
    ) {
      throw new Error("Package pricing could not be loaded. Please refresh.");
    }
    keys.add(plan.key);
  }
  return {
    plans: value.plans as Plan[],
    checkout_enabled: value.checkout_enabled,
    draft: value.draft,
  };
}

export function money(amount: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: amount % 100 ? 2 : 0,
  }).format(amount / 100);
}
export function hours(minutes: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(
    minutes / 60,
  );
}

export async function billingRequest<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/billing/${path}`, {
      method,
      cache: "no-store",
      redirect: "error",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    throw new Error(
      "Billing is taking longer than expected. Keep any saved purchase request and retry it.",
    );
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "The billing response could not be read. Keep any saved purchase request and refresh billing.",
    );
  }
  if (!response.ok) {
    const detail = isRecord(data) && isRecord(data.error) ? data.error : {};
    throw new Error(
      typeof detail.message === "string"
        ? detail.message
        : "Billing is temporarily unavailable. Please try again.",
    );
  }
  if (path === "plans") return parseCatalog(data) as T;
  return data as T;
}

export function checkoutRedirect(url: string, kind: "checkout" | "portal") {
  const parsed = new URL(url);
  const host =
    kind === "checkout" ? "checkout.stripe.com" : "billing.stripe.com";
  if (
    parsed.protocol !== "https:" ||
    parsed.hostname !== host ||
    parsed.username ||
    parsed.password ||
    (parsed.port && parsed.port !== "443")
  ) {
    throw new Error(
      "The payment link could not be confirmed. Please refresh billing.",
    );
  }
  window.location.assign(parsed.href);
}
