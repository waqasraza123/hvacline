import { describe, expect, it } from "vitest";
import {
  normalizeCallCode, parsePhoneAccessList, parsePhoneAccessPreview, requireCallApproval,
} from "./phone-access-model";

const preview = {
  id: "00000000-0000-4000-8000-000000000001", business_name: "Fictional HVAC",
  caller_last_four: "1002", called_last_four: "1001",
  created_at: "2026-11-26T10:00:00Z", expires_at: "2026-11-26T10:03:00Z",
  share_memory: false, memory_available: true,
};

describe("telephone account approval", () => {
  it("normalizes spoken call groups without accepting authenticator or recovery codes", () => {
    expect(normalizeCallCode("call abcd 1234 ffff")).toBe("CALL-ABCD-1234-FFFF");
    expect(() => normalizeCallCode("123456")).toThrow();
    expect(() => normalizeCallCode("CALL-ABCD-1234-GGGG")).toThrow();
    expect(() => normalizeCallCode("https://another.example/CALL-ABCD-1234-FFFF")).toThrow();
  });

  it("requires current call details and never defaults malformed approvals to active", () => {
    expect(parsePhoneAccessPreview(preview)).toEqual(preview);
    expect(() => parsePhoneAccessPreview({ ...preview, caller_last_four: "+15559991002" })).toThrow();
    expect(() => parsePhoneAccessPreview({ ...preview, expires_at: "invalid" })).toThrow();
    expect(() => parsePhoneAccessPreview({ ...preview, share_memory: "true" })).toThrow();
    expect(() => parsePhoneAccessList({ items: [{ ...preview, status: "PENDING" }] })).toThrow();
    expect(parsePhoneAccessList({ items: [{ ...preview, status: "REVOKED" }] })[0].status).toBe("REVOKED");
    expect(() => parsePhoneAccessList({ items: [{ ...preview, status: "ACTIVE" }, { ...preview, status: "ACTIVE" }] })).toThrow();
  });

  it("requires a matching unexpired positive approval before showing success", () => {
    const result = { id: preview.id, approved: true, expires_at: new Date(Date.now() + 120000).toISOString() };
    expect(() => requireCallApproval(result, preview.id)).not.toThrow();
    expect(() => requireCallApproval({ ...result, approved: false }, preview.id)).toThrow();
    expect(() => requireCallApproval(result, "other")).toThrow();
    expect(() => requireCallApproval({ ...result, expires_at: preview.created_at }, preview.id)).toThrow();
  });
});
