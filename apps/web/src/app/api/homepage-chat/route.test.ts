import { NextRequest } from "next/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("@/features/customer/server", () => ({ currentCustomer: vi.fn() }));
import { currentCustomer } from "@/features/customer/server";
import { GET, POST } from "./route";

const origin = "https://hvacline.example";
const token = "t".repeat(43);
const body = {
  message: "Can you help with AC repair?",
  request_id: "00000000-0000-4000-8000-000000000001",
  ai_disclosure_accepted: true,
};

beforeEach(() => {
  vi.mocked(currentCustomer).mockResolvedValue({ status: "anonymous" });
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example");
  vi.stubEnv(
    "CUSTOMER_PORTAL_SECRET",
    "test-server-only-portal-secret-32-chars",
  );
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function post(overrides: Record<string, string> = {}) {
  return new NextRequest(origin + "/api/homepage-chat", {
    method: "POST",
    body: JSON.stringify(body),
    headers: {
      origin,
      "content-type": "application/json",
      cookie: `hvacline-visitor=${token}; __Host-hvacline-visitor=${token}`,
      ...overrides,
    },
  });
}

it("issues a private visitor cookie and never returns provider credentials", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(Response.json({ state: "ready", remaining: 1 })),
  );
  const response = await GET(new NextRequest(origin + "/api/homepage-chat"));
  expect(await response.json()).toEqual({ state: "ready", remaining: 1 });
  expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  expect(response.headers.get("cache-control")).toBe("no-store");
});

it("rejects cross-origin attempts before calling the provider", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  expect((await POST(post({ origin: "https://other.example" }))).status).toBe(
    403,
  );
  expect(fetcher).not.toHaveBeenCalled();
});

it("requires the previously issued cookie before a generation", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const response = await POST(post({ cookie: "" }));
  expect(response.status).toBe(409);
  expect(fetcher).not.toHaveBeenCalled();
});

it("routes authenticated customers to continuation without spending the trial", async () => {
  vi.mocked(currentCustomer).mockResolvedValue({
    status: "authenticated",
    user: {
      id: "test",
      full_name: "Test Customer",
      email: "test@example.test",
    },
  });
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const response = await POST(post());
  expect(await response.json()).toEqual({ state: "authenticated" });
  expect(fetcher).not.toHaveBeenCalled();
});

it("preserves the backend sign-in gate instead of generating a second answer", async () => {
  const fetcher = vi.fn().mockResolvedValue(
    Response.json(
      {
        error: {
          code: "HOMEPAGE_SIGN_IN_REQUIRED",
          message: "Sign in to continue with Line.",
        },
      },
      { status: 403 },
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  const response = await POST(post());
  expect(response.status).toBe(403);
  expect((await response.json()).error.code).toBe("HOMEPAGE_SIGN_IN_REQUIRED");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][1].headers["X-Homepage-Visitor"]).toBe(token);
});
