import type { Operations } from "@/features/operations/api";

export type Role = "OWNER" | "ADMIN" | "STAFF";
export type StaffUser = { id: string; display_name: string; email: string; businesses: { id: string; name: string; role: Role }[] };
export type Member = { id: string; user_id: string; display_name: string; email: string | null; role: Role; active: boolean; row_version: number };
export type Invitation = { id: string; email: string; role: Role; row_version: number; expires_at: string; consumed: boolean; revoked: boolean };
export type Team = { role: Role; members: Member[]; invitations: Invitation[] };

export function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null; }
export function isRole(value: unknown): value is Role { return value === "OWNER" || value === "ADMIN" || value === "STAFF"; }
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export class WorkspaceError extends Error { constructor(readonly status: number, message: string) { super(message); } }
export function identifier(value: string): string { if (!uuid.test(value)) throw new Error("The workspace reference is invalid. Reload the page."); return value; }

export async function workspaceRequest(path: string, method = "GET", body?: unknown): Promise<unknown> {
  const response = await fetch(`/api/workspace/${path}`, { method, cache: "no-store", redirect: "error",
    headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(20000) });
  if (response.status === 204) return null;
  const result: unknown = await response.json();
  if (!response.ok) throw new WorkspaceError(response.status, isRecord(result) && isRecord(result.error) && typeof result.error.message === "string" ? result.error.message : "The workspace request could not be completed.");
  return result;
}

export function parseStaffUser(value: unknown): StaffUser {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.display_name !== "string" || typeof value.email !== "string" || !Array.isArray(value.businesses)) throw new Error("Staff identity could not be loaded.");
  identifier(value.id);
  const businesses = value.businesses.map((item: unknown) => {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.name !== "string" || !isRole(item.role)) throw new Error("Business access could not be loaded.");
    return { id: identifier(item.id), name: item.name, role: item.role };
  });
  return { id: value.id, display_name: value.display_name, email: value.email, businesses };
}

export function parseInvitation(value: unknown): Invitation {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.email !== "string" || !isRole(value.role) ||
    typeof value.row_version !== "number" || !Number.isSafeInteger(value.row_version) || value.row_version < 1 ||
    typeof value.expires_at !== "string" || !Number.isFinite(Date.parse(value.expires_at)) || typeof value.consumed !== "boolean" || typeof value.revoked !== "boolean") throw new Error("Invitation data could not be verified.");
  return { id: identifier(value.id), email: value.email, role: value.role, row_version: value.row_version, expires_at: value.expires_at, consumed: value.consumed, revoked: value.revoked };
}

export function parseTeam(value: unknown): Team {
  if (!isRecord(value) || !isRole(value.role) || !Array.isArray(value.members) || !Array.isArray(value.invitations)) throw new Error("Team data could not be loaded.");
  const members: Member[] = value.members.map((item: unknown) => {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.user_id !== "string" || typeof item.display_name !== "string" || (item.email !== null && typeof item.email !== "string") || !isRole(item.role) || typeof item.active !== "boolean" || typeof item.row_version !== "number" || !Number.isSafeInteger(item.row_version) || item.row_version < 1) throw new Error("Team member data could not be verified.");
    return { id: identifier(item.id), user_id: identifier(item.user_id), display_name: item.display_name, email: item.email, role: item.role, active: item.active, row_version: item.row_version };
  });
  return { role: value.role, members, invitations: value.invitations.map(parseInvitation) };
}

export function parseInvitationToken(value: unknown): string {
  if (!isRecord(value) || typeof value.invitation_token !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(value.invitation_token)) throw new Error("The invitation link was not confirmed. Reload saved invitations before creating another.");
  return value.invitation_token;
}

export function parseWorkspaceOperations(value: unknown): Operations {
  if (!isRecord(value) || !Array.isArray(value.calls) || !Array.isArray(value.appointments) || !Array.isArray(value.service_requests) || !Array.isArray(value.handoffs)) throw new Error("The business queue could not be loaded.");
  const validDate = (item: unknown) => typeof item === "string" && Number.isFinite(Date.parse(item));
  for (const item of value.calls) {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.status !== "string" || !validDate(item.received_at) || item.caller_number !== null && typeof item.caller_number !== "string") throw new Error("Call data could not be loaded.");
  }
  for (const item of value.appointments) {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.service_request_id !== "string" || typeof item.status !== "string" || typeof item.team_key !== "string" || !validDate(item.starts_at) || !validDate(item.ends_at) || !validDate(item.hold_expires_at)) throw new Error("Appointment data could not be loaded.");
  }
  for (const item of value.service_requests) {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.status !== "string" || !validDate(item.confirmed_at) ||
      !isRecord(item.customer) || typeof item.customer.full_name !== "string" || typeof item.customer.phone !== "string" ||
      !isRecord(item.customer.address) || typeof item.customer.address.line1 !== "string" || typeof item.customer.address.city !== "string" || typeof item.customer.address.state_code !== "string" || typeof item.customer.address.postal_code !== "string" ||
      !isRecord(item.service) || typeof item.service.kind !== "string" || typeof item.service.equipment_issue !== "string" || typeof item.service.preferred_window !== "string" || typeof item.service.hazardous_condition !== "boolean") throw new Error("Service request data could not be loaded.");
  }
  for (const item of value.handoffs) {
    if (!isRecord(item) || typeof item.id !== "string" || typeof item.lead_id !== "string" || typeof item.kind !== "string" || typeof item.status !== "string" || typeof item.reason !== "string" ||
      item.row_version !== undefined && (typeof item.row_version !== "number" || !Number.isSafeInteger(item.row_version) || item.row_version < 1) ||
      item.created_at !== undefined && !validDate(item.created_at) ||
      item.availability !== undefined && item.availability !== null && typeof item.availability !== "string" ||
      item.preferred_contact_method !== undefined && typeof item.preferred_contact_method !== "string") throw new Error("Follow-up data could not be loaded.");
    if (item.customer !== undefined && item.customer !== null && (!isRecord(item.customer) || typeof item.customer.full_name !== "string" || item.customer.phone !== null && typeof item.customer.phone !== "string" || item.customer.email !== null && typeof item.customer.email !== "string")) throw new Error("Follow-up contact data could not be loaded.");
    identifier(item.id);
  }
  return value as Operations;
}
