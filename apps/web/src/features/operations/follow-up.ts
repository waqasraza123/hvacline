import { requestApi } from "./api";
import type { FollowUp } from "./api";

export const followUpActions = {
  ACKNOWLEDGED: "Acknowledge",
  COMPLETED: "Mark complete",
  CANCELLED: "Cancel follow-up",
} as const;

export type FollowUpAction = keyof typeof followUpActions;

export function allowedFollowUpActions(row: FollowUp): FollowUpAction[] {
  if (!Number.isSafeInteger(row.row_version) || (row.row_version ?? 0) < 1) return [];
  if (row.status === "REQUESTED") return ["ACKNOWLEDGED", "COMPLETED", "CANCELLED"];
  if (row.status === "ACKNOWLEDGED") return ["COMPLETED", "CANCELLED"];
  return [];
}

export function followUpAge(value: string | undefined, now: number): string {
  const time = value ? Date.parse(value) : NaN;
  if (!Number.isFinite(time) || time > now) return "Age unavailable";
  const minutes = Math.floor((now - time) / 60000);
  if (minutes < 1) return "Under a minute";
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr`;
  return `${Math.floor(minutes / 1440)} days`;
}

export function filterFollowUps(rows: FollowUp[], status: string, kind: string, query: string): FollowUp[] {
  const search = query.trim().toLocaleLowerCase();
  return rows.filter((row) =>
    (status === "ALL" || row.status === status) &&
    (kind === "ALL" || row.kind === kind) &&
    (!search || [row.reason, row.customer?.full_name, row.customer?.phone, row.customer?.email]
      .some((value) => value?.toLocaleLowerCase().includes(search))),
  ).sort((a, b) => {
    const left = Date.parse(a.created_at ?? "");
    const right = Date.parse(b.created_at ?? "");
    return Number.isFinite(left) && Number.isFinite(right) ? left - right : a.id.localeCompare(b.id);
  });
}

export async function updateFollowUp(apiBaseUrl: string, token: string, row: FollowUp, status: FollowUpAction, demo: boolean): Promise<FollowUp> {
  if (demo) throw new Error("Connect a workspace to update follow-up.");
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(row.id)) {
    throw new Error("The follow-up reference is invalid. Refresh the workspace.");
  }
  if (!allowedFollowUpActions(row).includes(status)) {
    throw new Error("This action is unavailable. Refresh the workspace before continuing.");
  }
  const response = await requestApi<unknown>(apiBaseUrl, token, `handoff-requests/${row.id}/status`, "POST", {
    status,
    expected_row_version: row.row_version,
  });
  if (typeof response !== "object" || response === null ||
    !("id" in response) || response.id !== row.id ||
    !("lead_id" in response) || response.lead_id !== row.lead_id ||
    !("status" in response) || response.status !== status ||
    !("row_version" in response) || typeof response.row_version !== "number" ||
    !Number.isSafeInteger(response.row_version) || response.row_version <= (row.row_version ?? 0)) {
    throw new Error("The saved outcome could not be confirmed. Refresh follow-up before another action.");
  }
  return { ...row, status, row_version: response.row_version };
}
