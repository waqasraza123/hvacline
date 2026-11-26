import { afterEach, expect, it, vi } from "vitest";
import { loadStaffAlerts, parseStaffAlertPolicy, parseStaffAlerts, saveStaffAlertPolicy } from "./staff-alerts";

const policy = { enabled: false, recipients: [], row_version: 2, runtime_enabled: true, sender: "alerts@example.com" };

afterEach(() => vi.unstubAllGlobals());

it("rejects invalid staff policy versions and unrecognized delivery states", () => {
  expect(parseStaffAlertPolicy(policy).row_version).toBe(2);
  expect(() => parseStaffAlertPolicy({ ...policy, row_version: -1 })).toThrow("invalid data");
  expect(() => parseStaffAlertPolicy({ ...policy, recipients: [null] })).toThrow("invalid data");
  expect(() => parseStaffAlerts({ policy, recent: [{ status: "DELIVERED" }] })).toThrow("invalid data");
});

it("keeps provider acceptance separate from delivery confirmation", () => {
  const data = parseStaffAlerts({ policy, recent: [{ id: "fictional-alert", event_type: "HANDOFF", source_id: "fictional-source", recipient: "staff@example.com", status: "ACCEPTED", delivery_status: null, attempts: 1, created_at: "2026-11-26T10:00:00Z", due_at: "2026-11-26T10:00:00Z", last_error: null }] });
  expect(data.recent[0].status).toBe("ACCEPTED");
  expect(data.recent[0].delivery_status).toBeNull();
});

it("loads protected settings and saves with a version without requesting a test send", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ policy, recent: [] })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...policy, enabled: true, recipients: ["staff@example.com"], row_version: 3 })));
  vi.stubGlobal("fetch", fetcher);
  await loadStaffAlerts("https://api.example.com", "fictional-admin");
  const result = await saveStaffAlertPolicy("https://api.example.com", "fictional-admin", policy, true, ["staff@example.com"]);
  expect(result.row_version).toBe(3);
  expect(fetcher).toHaveBeenCalledTimes(2);
  const [url, options] = fetcher.mock.calls[1];
  expect(url).toBe("https://api.example.com/api/v1/development/staff-alerts");
  expect(options.method).toBe("PUT");
  expect(options.headers["X-Demo-Admin-Token"]).toBe("fictional-admin");
  expect(JSON.parse(options.body)).toEqual({ enabled: true, recipients: ["staff@example.com"], expected_row_version: 2 });
});
