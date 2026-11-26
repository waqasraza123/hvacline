import { expect, it } from "vitest";
import { identifier, parseInvitation, parseStaffUser, parseTeam, parseWorkspaceOperations } from "./api";

const id = "00000000-0000-4000-8000-000000000001";
it("accepts only recognized business roles and staff identities", () => {
  expect(parseStaffUser({ id, email: "staff@example.com", display_name: "Fictional Staff", businesses: [{ id, name: "Fictional Business", role: "STAFF" }] }).businesses[0].role).toBe("STAFF");
  expect(() => parseStaffUser({ id, email: "staff@example.com", display_name: "Fictional Staff", businesses: [{ id, name: "Fictional Business", role: "SUPER_ADMIN" }] })).toThrow("Business access");
  expect(() => identifier("../other-business")).toThrow("invalid");
});

it("retains consumed/revoked invitation state and rejects unversioned changes", () => {
  const invite = { id, email: "invited@example.com", role: "STAFF", row_version: 2, consumed: false, revoked: true, expires_at: "2026-11-28T10:00:00Z" };
  expect(parseInvitation(invite).revoked).toBe(true);
  expect(() => parseInvitation({ ...invite, row_version: 0 })).toThrow("verified");
  expect(() => parseTeam({ role: "OWNER", members: [{ id, user_id: id, display_name: "Fictional Staff", email: null, role: "OWNER", active: true, row_version: 0 }], invitations: [] })).toThrow("verified");
});

it("allows genuinely empty business queues without substituting samples", () => {
  expect(parseWorkspaceOperations({ calls: [], appointments: [], service_requests: [], handoffs: [] })).toEqual({ calls: [], appointments: [], service_requests: [], handoffs: [] });
  expect(() => parseWorkspaceOperations({ calls: [], appointments: [], service_requests: [], handoffs: [{ id, lead_id: id, kind: "CALLBACK", status: "REQUESTED", reason: "Example", customer: { full_name: {} } }] })).toThrow("contact data");
});
