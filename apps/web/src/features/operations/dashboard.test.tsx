import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import type { Operations } from "./api";
import { DashboardOverview } from "./dashboard-overview";
import { DashboardShell } from "./dashboard-shell";

it("retains the existing section destinations while gating browser voice", () => {
  const render = (connected: boolean, conversationAiEnabled: boolean) => renderToStaticMarkup(createElement(DashboardShell, {
    section: "recovery",
    onSelect: () => {},
    connected,
    busy: false,
    demo: true,
    conversationAiEnabled,
    onRefresh: () => {},
    children: null,
  }));
  const connected = render(true, false);
  for (const label of ["Overview", "Calls &amp; conversations", "Leads &amp; requests", "Appointments", "Follow-up", "AI Lead Recovery", "Voice &amp; languages", "Knowledge base", "Agent settings", "Scheduling", "GoHighLevel", "Maintenance hours", "Websites"]) {
    expect(connected).toContain(`aria-label="${label}"`);
  }
  expect(connected).not.toContain('aria-label="Browser voice"');
  expect(render(true, true)).toContain('aria-label="Browser voice"');
  expect(connected.match(/aria-current="page"/g)).toHaveLength(1);
  expect(connected).toContain("Fictional sample data");
  const disconnected = render(false, true);
  const nav = disconnected.match(/<nav\b[^>]*aria-label="Operations sections"[\s\S]*?<\/nav>/)?.[0] ?? "";
  const buttons = nav.match(/<button\b[^>]*>/g) ?? [];
  expect(buttons).toHaveLength(14);
  for (const button of buttons) expect(button).toContain('disabled=""');
});

it("uses only loaded records for counts and the five most recent calls", () => {
  const data: Operations = {
    calls: Array.from({ length: 7 }, (_, index) => ({
      id: `fictional-call-${index}`,
      caller_number: index === 6 ? null : `Fictional caller ${index}`,
      received_at: `2026-11-24T10:0${index}:00Z`,
      status: "RECEIVED",
    })),
    service_requests: [],
    appointments: [
      { id: "past", service_request_id: "fictional-past", team_key: "demo-team", starts_at: "2026-11-23T10:00:00Z", ends_at: "2026-11-23T11:00:00Z", hold_expires_at: "2026-11-23T09:00:00Z", status: "CONFIRMED" },
      { id: "next", service_request_id: "fictional-next", team_key: "demo-team", starts_at: "2026-11-25T10:00:00Z", ends_at: "2026-11-25T11:00:00Z", hold_expires_at: "2026-11-25T09:00:00Z", status: "CONFIRMED" },
      { id: "held", service_request_id: "fictional-held", team_key: "demo-team", starts_at: "2026-11-25T12:00:00Z", ends_at: "2026-11-25T13:00:00Z", hold_expires_at: "2026-11-25T11:00:00Z", status: "HELD" },
    ],
    handoffs: [
      { id: "open", kind: "CALLBACK", status: "REQUESTED", reason: "Fictional callback", lead_id: "fictional-open" },
      { id: "closed", kind: "CALLBACK", status: "COMPLETED", reason: "Fictional completed callback", lead_id: "fictional-closed" },
    ],
  };
  const html = renderToStaticMarkup(createElement(DashboardOverview, {
    data,
    schedule: null,
    loadedAt: Date.parse("2026-11-24T12:00:00Z"),
    timestamp: (value: string) => value,
    onSelect: () => {},
  }));
  expect(html).toMatch(/Total calls[\s\S]*?<strong[^>]*>7<\/strong>/);
  expect(html).toMatch(/Confirmed bookings[\s\S]*?<strong[^>]*>2<\/strong>/);
  expect(html).toMatch(/Pending follow-up[\s\S]*?<strong[^>]*>1<\/strong>/);
  expect(html).not.toContain("2026-11-23T10:00:00Z");
  expect(html).not.toContain("Fictional completed callback");
  const recent = html.match(/<section\b[^>]*aria-label="Recent conversations"[\s\S]*?<\/section>/)?.[0] ?? "";
  expect(recent).toContain("Caller number unavailable");
  expect(recent).not.toContain("Fictional caller 1");
  expect(recent.indexOf("2026-11-24T10:06:00Z")).toBeLessThan(recent.indexOf("2026-11-24T10:05:00Z"));
  expect(recent.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0].match(/<tr>/g)).toHaveLength(5);
  expect(data.calls[0].id).toBe("fictional-call-0");
});

it("renders empty loaded queues without substituting sample records", () => {
  const html = renderToStaticMarkup(createElement(DashboardOverview, {
    data: { calls: [], service_requests: [], appointments: [], handoffs: [] },
    schedule: null,
    loadedAt: Date.parse("2026-11-24T12:00:00Z"),
    timestamp: (value: string) => value,
    onSelect: () => {},
  }));
  expect(html).toContain("No calls in this queue");
  expect(html).toContain("No upcoming visits in this queue");
  expect(html).toContain("No pending follow-up in this queue");
  expect(html).not.toContain("Sample homeowner");
});
