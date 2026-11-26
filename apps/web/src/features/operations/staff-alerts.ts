import { requestApi } from "./api";

export type StaffAlertPolicy = { enabled: boolean; recipients: string[]; row_version: number; runtime_enabled: boolean; sender: string | null };
export type StaffAlert = {
  id: string; event_type: string; source_id: string; recipient: string; status: string;
  delivery_status: string | null; attempts: number; created_at: string; due_at: string; last_error: string | null;
};
export type StaffAlerts = { policy: StaffAlertPolicy; recent: StaffAlert[] };

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseStaffAlertPolicy(value: unknown): StaffAlertPolicy {
  if (!record(value) || typeof value.enabled !== "boolean" || typeof value.runtime_enabled !== "boolean" ||
    typeof value.row_version !== "number" || !Number.isSafeInteger(value.row_version) || value.row_version < 0 ||
    !Array.isArray(value.recipients) || value.recipients.length > 5 || !value.recipients.every((item) => typeof item === "string") ||
    (value.sender !== null && typeof value.sender !== "string")) throw new Error("Staff alert settings returned invalid data.");
  return { enabled: value.enabled, recipients: value.recipients, row_version: value.row_version, runtime_enabled: value.runtime_enabled, sender: value.sender };
}

export function parseStaffAlerts(value: unknown): StaffAlerts {
  if (!record(value) || !Array.isArray(value.recent) || value.recent.length > 100) throw new Error("Staff alert history returned invalid data.");
  const recent: StaffAlert[] = value.recent.map((item: unknown) => {
    if (!record(item) || !["HANDOFF", "URGENT_SERVICE"].includes(String(item.event_type)) ||
      !["PENDING", "ACCEPTED", "SKIPPED", "FAILED", "UNKNOWN"].includes(String(item.status)) ||
      typeof item.id !== "string" || typeof item.source_id !== "string" || typeof item.recipient !== "string" ||
      typeof item.created_at !== "string" || !Number.isFinite(Date.parse(item.created_at)) ||
      typeof item.due_at !== "string" || !Number.isFinite(Date.parse(item.due_at)) ||
      typeof item.attempts !== "number" || !Number.isSafeInteger(item.attempts) || item.attempts < 0 ||
      (item.last_error !== null && typeof item.last_error !== "string") || (item.delivery_status !== null && typeof item.delivery_status !== "string")) throw new Error("Staff alert history returned invalid data.");
    return { id: item.id, event_type: String(item.event_type), source_id: item.source_id, recipient: item.recipient, status: String(item.status), delivery_status: item.delivery_status, attempts: item.attempts, created_at: item.created_at, due_at: item.due_at, last_error: item.last_error };
  });
  return { policy: parseStaffAlertPolicy(value.policy), recent };
}

export async function loadStaffAlerts(apiBaseUrl: string, token: string): Promise<StaffAlerts> {
  return parseStaffAlerts(await requestApi<unknown>(apiBaseUrl, token, "staff-alerts"));
}

export async function saveStaffAlertPolicy(apiBaseUrl: string, token: string, policy: StaffAlertPolicy, enabled: boolean, recipients: string[]): Promise<StaffAlertPolicy> {
  return parseStaffAlertPolicy(await requestApi<unknown>(apiBaseUrl, token, "staff-alerts", "PUT", {
    enabled, recipients, expected_row_version: policy.row_version,
  }));
}
