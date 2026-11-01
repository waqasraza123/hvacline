export const callingLaunch = {
  date: "2026-11-05",
  label: "November 5, 2026",
} as const;

export const scenarios = {
  cooling: "My AC isn’t cooling",
  heating: "My heating isn’t working",
  maintenance: "I’m planning a tune-up",
} as const;

export type DemoScenario = keyof typeof scenarios;

export const callStatuses = [
  "reserved",
  "dialing",
  "in_progress",
  "processing",
  "unknown",
  "failed",
  "rejected",
  "unanswered",
  "completed",
  "disconnected",
] as const;

export type DemoCall = {
  id: string;
  status: (typeof callStatuses)[number];
  transfer_status:
    "not_requested" | "refer_accepted" | "failed" | "unconfirmed";
  created_at: string;
  terminal: boolean;
  message: string;
};

export const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isDemoCall(value: unknown): value is DemoCall {
  if (typeof value !== "object" || value === null) return false;
  const call = value as Record<string, unknown>;
  return (
    typeof call.id === "string" &&
    UUID_PATTERN.test(call.id) &&
    typeof call.status === "string" &&
    callStatuses.some((status) => status === call.status) &&
    typeof call.transfer_status === "string" &&
    ["not_requested", "refer_accepted", "failed", "unconfirmed"].includes(
      call.transfer_status,
    ) &&
    typeof call.created_at === "string" &&
    Number.isFinite(Date.parse(call.created_at)) &&
    typeof call.terminal === "boolean" &&
    call.terminal ===
      [
        "failed",
        "rejected",
        "unanswered",
        "completed",
        "disconnected",
      ].includes(call.status) &&
    typeof call.message === "string" &&
    call.message.length > 0 &&
    call.message.length <= 1000
  );
}
