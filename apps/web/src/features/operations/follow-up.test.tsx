import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import type { FollowUp } from "./api";
import { FollowUpQueue } from "./follow-up-queue";
import { allowedFollowUpActions, filterFollowUps, followUpAge, updateFollowUp } from "./follow-up";

const row: FollowUp = {
  id: "11111111-1111-4111-8111-111111111111",
  lead_id: "fictional-lead",
  kind: "CALLBACK",
  status: "REQUESTED",
  reason: "Fictional request for staff help",
  row_version: 2,
  created_at: "2026-11-26T08:00:00Z",
  customer: { full_name: "Fictional customer", phone: null, email: null },
};

afterEach(() => vi.unstubAllGlobals());

it("restricts transitions and refuses writes without a valid saved version", () => {
  expect(allowedFollowUpActions(row)).toEqual(["ACKNOWLEDGED", "COMPLETED", "CANCELLED"]);
  expect(allowedFollowUpActions({ ...row, status: "ACKNOWLEDGED" })).toEqual(["COMPLETED", "CANCELLED"]);
  for (const status of ["COMPLETED", "CANCELLED", "UNKNOWN"]) {
    expect(allowedFollowUpActions({ ...row, status })).toEqual([]);
  }
  expect(allowedFollowUpActions({ ...row, row_version: undefined })).toEqual([]);
  expect(allowedFollowUpActions({ ...row, row_version: 0 })).toEqual([]);
});

it("filters contact context and orders the loaded queue oldest first without mutation", () => {
  const newer = { ...row, id: "newer", kind: "LIVE_TRANSFER", status: "ACKNOWLEDGED", created_at: "2026-11-26T09:00:00Z" };
  const rows = [newer, row];
  expect(filterFollowUps(rows, "ALL", "ALL", "fictional CUSTOMER")).toEqual([row, newer]);
  expect(filterFollowUps(rows, "ACKNOWLEDGED", "LIVE_TRANSFER", "")).toEqual([newer]);
  expect(filterFollowUps(rows, "REQUESTED", "LIVE_TRANSFER", "")).toEqual([]);
  expect(rows[0]).toBe(newer);
  expect(followUpAge(row.created_at, Date.parse("2026-11-26T10:00:00Z"))).toBe("2 hr");
  expect(followUpAge("invalid", Date.now())).toBe("Age unavailable");
});

it("posts the loaded version and accepts only the matching confirmed outcome", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...row, status: "ACKNOWLEDGED", row_version: 3 })));
  vi.stubGlobal("fetch", fetcher);
  expect(await updateFollowUp("https://api.example.com", "fictional-admin", row, "ACKNOWLEDGED", false)).toMatchObject({ status: "ACKNOWLEDGED", row_version: 3 });
  const [url, options] = fetcher.mock.calls[0];
  expect(url).toBe(`https://api.example.com/api/v1/development/handoff-requests/${row.id}/status`);
  expect(options.headers["X-Demo-Admin-Token"]).toBe("fictional-admin");
  expect(JSON.parse(options.body)).toEqual({ status: "ACKNOWLEDGED", expected_row_version: 2 });
  fetcher.mockResolvedValue(new Response(JSON.stringify({ ...row, id: "other", status: "ACKNOWLEDGED", row_version: 3 })));
  await expect(updateFollowUp("", "", row, "ACKNOWLEDGED", false)).rejects.toThrow("outcome could not be confirmed");
});

it("never contacts the backend for demo, terminal or unversioned actions", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  await expect(updateFollowUp("", "", row, "COMPLETED", true)).rejects.toThrow("Connect a workspace");
  await expect(updateFollowUp("", "", { ...row, status: "COMPLETED" }, "CANCELLED", false)).rejects.toThrow("unavailable");
  await expect(updateFollowUp("", "", { ...row, row_version: undefined }, "COMPLETED", false)).rejects.toThrow("unavailable");
  expect(fetcher).not.toHaveBeenCalled();
});

it("renders read-only demo controls and retains contact availability wording", () => {
  const html = renderToStaticMarkup(createElement(FollowUpQueue, {
    rows: [row], demo: true, apiBaseUrl: "", token: "", loadedAt: Date.parse("2026-11-26T10:00:00Z"),
    busy: false, onBusyChange: () => {}, onReload: async () => {}, onUpdated: () => {}, timestamp: (value: string) => value,
  }));
  expect(html).toContain("Demo records are read-only");
  expect(html).toContain("No phone recorded");
  expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Acknowledge/);
  expect(html).toContain("2 hr");
});
