import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { currentCustomer } from "@/features/customer/server";
import { GET, POST } from "./route";

vi.mock("@/features/customer/server", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/customer/server")>()),
  currentCustomer: vi.fn(),
}));

const customerSession = vi.mocked(currentCustomer);
const fetcher = vi.fn<typeof fetch>();
const secret = "synthetic-outbound-bridge-secret-with-32-characters";
const visitor = "v".repeat(43);
const requestId = "10000000-0000-4000-8000-000000000001";
const call = {
  id: "10000000-0000-4000-8000-000000000002",
  status: "dialing",
  transfer_status: "not_requested",
  created_at: "2026-11-01T12:00:00Z",
  terminal: false,
  message: "The call was requested.",
};
const payload = {
  request_id: requestId,
  phone_number: "+15559990002",
  scenario: "cooling",
  consent: true,
  consent_version: "outbound-demo-v1",
};

function post(body: unknown = payload, origin = "https://hvacline.example") {
  return new NextRequest("https://hvacline.example/api/outbound-demo", {
    method: "POST",
    headers: {
      Origin: origin,
      "Content-Type": "application/json",
      Cookie: `hvacline-call-visitor=${visitor}`,
    },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  customerSession.mockReset();
  customerSession.mockResolvedValue({
    status: "authenticated",
    user: {
      id: "synthetic-callback-customer",
      full_name: "Synthetic Customer",
      email: "synthetic@example.test",
    },
  });
  fetcher.mockReset();
  vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("OUTBOUND_DEMO_FORM_ENABLED", "true");
  vi.stubEnv("OUTBOUND_DEMO_SECRET", secret);
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.hvacline.example");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("outbound demo bridge", () => {
  it("requires sign-in before availability or creating a callback", async () => {
    customerSession.mockResolvedValue({ status: "anonymous" });
    const available = await GET(
      new NextRequest("https://hvacline.example/api/outbound-demo"),
    );
    expect(available.status).toBe(401);
    expect((await available.json()).error.code).toBe("CALLBACK_SIGN_IN_REQUIRED");
    expect(available.cookies.get("hvacline-call-visitor")).toBeUndefined();
    const response = await POST(post());
    expect(response.status).toBe(401);
    expect(await response.json()).toMatchObject({
      error: { code: "CALLBACK_SIGN_IN_REQUIRED" },
      request_not_created: true,
    });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("requires sign-in for saved status without claiming the call was never created", async () => {
    customerSession.mockResolvedValue({ status: "anonymous" });
    const response = await GET(new NextRequest(
      `https://hvacline.example/api/outbound-demo?request_id=${requestId}`,
      { headers: { Cookie: `hvacline-call-visitor=${visitor}` } },
    ));
    expect(response.status).toBe(401);
    expect(await response.json()).not.toHaveProperty("request_not_created");
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("fails closed when the account service cannot verify sign-in", async () => {
    customerSession.mockResolvedValue({ status: "unavailable" });
    const response = await POST(post());
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({
      error: { code: "CALLBACK_AUTH_UNAVAILABLE" }, request_not_created: true,
    });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("revalidates sign-in at submission after an earlier availability check", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ available: true }));
    expect((await GET(new NextRequest(
      "https://hvacline.example/api/outbound-demo",
    ))).status).toBe(200);
    customerSession.mockResolvedValue({ status: "anonymous" });
    expect((await POST(post())).status).toBe(401);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][1]?.method).toBe("GET");
  });

  it("stays disabled without the explicit frontend gate", async () => {
    vi.stubEnv("OUTBOUND_DEMO_FORM_ENABLED", "false");
    expect(
      await (
        await GET(new NextRequest("https://hvacline.example/api/outbound-demo"))
      ).json(),
    ).toEqual({ available: false });
    expect((await POST(post())).status).toBe(503);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("rejects cross-origin requests before contacting the backend", async () => {
    expect(
      (await POST(post(payload, "https://untrusted.example"))).status,
    ).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each([
    { consent: false },
    { consent_version: "old" },
    { phone_number: "5551234" },
    { scenario: "campaign" },
    { transfer_number: "+15559990009" },
  ])(
    "rejects invalid consent, destinations and extra fields %j",
    async (change) => {
      expect((await POST(post({ ...payload, ...change }))).status).toBe(400);
      expect(fetcher).not.toHaveBeenCalled();
    },
  );

  it("forwards the stable request key and visitor only with server-side authorization", async () => {
    fetcher.mockResolvedValueOnce(Response.json(call));
    const response = await POST(post());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(call);
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.hvacline.example/api/v1/outbound-demo/calls",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
        redirect: "error",
        cache: "no-store",
        headers: expect.objectContaining({
          "X-Outbound-Demo-Key": secret,
          "X-Outbound-Visitor": visitor,
        }),
      }),
    );
    expect(response.headers.get("X-Outbound-Demo-Key")).toBeNull();
    expect(response.headers.get("Cache-Control")).toBe("no-store");
  });

  it("creates a private recovery cookie at availability", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ available: true }));
    const response = await GET(
      new NextRequest("https://hvacline.example/api/outbound-demo"),
    );
    expect(response.cookies.get("hvacline-call-visitor")).toMatchObject({
      httpOnly: true,
      sameSite: "strict",
      path: "/",
      maxAge: 86400,
    });
  });

  it("retains status access when new website calls are disabled", async () => {
    vi.stubEnv("OUTBOUND_DEMO_FORM_ENABLED", "false");
    fetcher.mockResolvedValueOnce(Response.json(call));
    const request = new NextRequest(
      `https://hvacline.example/api/outbound-demo?request_id=${requestId}`,
      { headers: { Cookie: `hvacline-call-visitor=${visitor}` } },
    );
    expect((await GET(request)).status).toBe(200);
    expect(fetcher).toHaveBeenCalledWith(
      expect.stringContaining(`/requests/${requestId}`),
      expect.anything(),
    );
  });

  it("does not retry an ambiguous POST or expose provider errors", async () => {
    fetcher.mockRejectedValueOnce(
      new Error("synthetic private provider diagnostic"),
    );
    const response = await POST(post());
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.request_not_created).not.toBe(true);
    expect(JSON.stringify(body)).not.toContain("private provider diagnostic");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it.each([
    { status: 403, code: "DEMO_NUMBER_NOT_AUTHORIZED" },
    { status: 429, code: "DEMO_CALL_LIMIT" },
    { status: 422, code: "DEMO_PHONE_NUMBER_INVALID" },
    { status: 422, code: "DEMO_DESTINATION_UNSUPPORTED" },
  ])(
    "permits form correction after a known rejection ($status)",
    async ({ status, code }) => {
      fetcher.mockResolvedValueOnce(
        Response.json({ error: { code } }, { status }),
      );
      const response = await POST(post());
      expect(response.status).toBe(status);
      expect(await response.json()).toMatchObject({
        request_not_created: true,
      });
      expect(fetcher).toHaveBeenCalledTimes(1);
    },
  );

  it("keeps recovery locked for an unrecognized upstream rejection", async () => {
    fetcher.mockResolvedValueOnce(
      Response.json({ error: { code: "UNKNOWN" } }, { status: 403 }),
    );
    const response = await POST(post());
    expect((await response.json()).request_not_created).not.toBe(true);
  });

  it("rejects contradictory terminal status data", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ ...call, terminal: true }));
    expect((await POST(post())).status).toBe(503);
  });
});
