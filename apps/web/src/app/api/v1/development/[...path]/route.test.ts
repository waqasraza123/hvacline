import { NextRequest } from "next/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GET, POST } from "./route";

const cookieStore = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("next/headers", () => ({ cookies: async () => cookieStore }));
const fetcher = vi.fn<typeof fetch>();
const id = "00000000-0000-4000-8000-000000000001";
const context = (path: string) => ({
  params: Promise.resolve({ path: path.split("/") }),
});

it("does not forward cross-origin memory or account-link changes", async () => {
  const path = "memory/whatsapp/link";
  const response = await POST(new NextRequest(
    `https://hvacline.example/api/v1/development/${path}`, {
      method: "POST", headers: { Origin: "https://another.example", "Content-Type": "application/json" },
      body: "{}",
    },
  ), context(path));
  expect(response.status).toBe(403);
  expect(fetcher).not.toHaveBeenCalled();
});

beforeEach(() => {
  fetcher.mockReset();
  cookieStore.get.mockReturnValue({ value: "synthetic-customer-session" });
  vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com");
  vi.stubEnv(
    "CUSTOMER_PORTAL_SECRET",
    "synthetic-portal-secret-at-least-32-characters",
  );
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

it("forwards owned booking details through the authenticated customer backend", async () => {
  fetcher.mockResolvedValueOnce(Response.json({ appointment: { id } }));
  const path = `appointments/${id}`;
  const response = await GET(
    new NextRequest(`https://hvacline.example/api/v1/development/${path}`),
    context(path),
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("Cache-Control")).toBe("no-store");
  expect(fetcher).toHaveBeenCalledWith(
    `https://api.example.com/api/v1/customer/${path}`,
    expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: "Bearer synthetic-customer-session",
      }),
    }),
  );
});

it("forwards the signed-in customer's limits without caching", async () => {
  fetcher.mockResolvedValueOnce(
    Response.json({ max_active_appointments: 1, max_booking_changes: 1 }),
  );
  const response = await GET(
    new NextRequest(
      "https://hvacline.example/api/v1/development/booking-limits",
    ),
    context("booking-limits"),
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("Cache-Control")).toBe("no-store");
  expect(fetcher).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/customer/booking-limits",
    expect.objectContaining({ method: "GET" }),
  );
});

it.each(["availability", "reschedule"])(
  "allows same-origin booking %s",
  async (action) => {
    fetcher.mockResolvedValueOnce(Response.json({ ok: true }));
    const path = `appointments/${id}/${action}`;
    const response = await POST(
      new NextRequest(`https://hvacline.example/api/v1/development/${path}`, {
        method: "POST",
        headers: {
          Origin: "https://hvacline.example",
          "Content-Type": "application/json",
        },
        body: "{}",
      }),
      context(path),
    );
    expect(response.status).toBe(200);
  },
);

it("rejects cross-origin edits and unrelated routes before contacting the backend", async () => {
  const path = `appointments/${id}/reschedule`;
  const response = await POST(
    new NextRequest(`https://hvacline.example/api/v1/development/${path}`, {
      method: "POST",
      headers: {
        Origin: "https://another.example",
        "Content-Type": "application/json",
      },
      body: "{}",
    }),
    context(path),
  );
  expect(response.status).toBe(403);
  expect(
    (
      await GET(
        new NextRequest(
          "https://hvacline.example/api/v1/development/hvac/operations",
        ),
        context("hvac/operations"),
      )
    ).status,
  ).toBe(404);
  expect(fetcher).not.toHaveBeenCalled();
});
