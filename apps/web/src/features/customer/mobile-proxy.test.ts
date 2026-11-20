import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mobilePathAllowed, proxyMobileRequest } from "./mobile-proxy";

const fetcher = vi.fn<typeof fetch>();
const token = "fictional-mobile-session-token-for-tests";
const portal = "fictional-server-only-portal-key-for-tests";
const id = "00000000-0000-4000-8000-000000000001";

function request(
  path: string,
  method = "GET",
  headers: Record<string, string> = {},
) {
  return new NextRequest(`https://hvacline.example/api/mobile/${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...headers,
    },
    ...(method === "POST" ? { body: "{}" } : {}),
  });
}

beforeEach(() => {
  fetcher.mockReset();
  vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("MOBILE_API_ENABLED", "true");
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.hvacline.example");
  vi.stubEnv("CUSTOMER_PORTAL_SECRET", portal);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("native customer gateway", () => {
  it("stays disabled without explicit server activation", async () => {
    vi.stubEnv("MOBILE_API_ENABLED", "false");
    expect(
      (await proxyMobileRequest(request("appointments"), ["appointments"]))
        .status,
    ).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each([
    "operations",
    "auth/admin",
    `appointments/${id}/cancel`,
    `conversation-sessions/${id}/booking/../hazard`,
    "websites",
    "billing/plans",
  ])("rejects unlisted route %s", async (path) => {
    expect(
      (await proxyMobileRequest(request(path, "POST"), path.split("/"))).status,
    ).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("requires a bearer even when browser cookies exist", async () => {
    const value = request("appointments", "GET", {
      Authorization: "",
      Cookie: "hvacline-session=fictional-cookie",
    });
    expect((await proxyMobileRequest(value, ["appointments"])).status).toBe(
      401,
    );
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("rejects browser-origin requests", async () => {
    expect(
      (
        await proxyMobileRequest(
          request("auth/login", "POST", { Origin: "https://hvacline.example" }),
          ["auth", "login"],
        )
      ).status,
    ).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("sends only the scoped bearer and server-owned portal key upstream", async () => {
    fetcher.mockResolvedValueOnce(
      Response.json(
        { appointments: [], timezone: "UTC" },
        {
          headers: {
            "Set-Cookie": "upstream-cookie=fictional",
            "X-Customer-Portal-Key": portal,
          },
        },
      ),
    );
    const response = await proxyMobileRequest(
      request("appointments", "GET", {
        "X-Customer-Portal-Key": "untrusted-client-value",
        "X-Demo-Admin-Token": "untrusted-admin",
        Cookie: "browser-cookie=fictional",
      }),
      ["appointments"],
    );
    expect(response.status).toBe(200);
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.hvacline.example/api/v1/customer/appointments",
      expect.objectContaining({
        headers: {
          "Content-Type": "application/json",
          "X-Customer-Portal-Key": portal,
          Authorization: `Bearer ${token}`,
        },
        redirect: "error",
        cache: "no-store",
      }),
    );
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("x-customer-portal-key")).toBeNull();
    expect(response.headers.get("cache-control")).toContain("no-store");
    expect(await response.text()).not.toContain(portal);
  });

  it("returns an MFA challenge to native callers without creating web cookies", async () => {
    const result = {
      mfa_required: true,
      next_action: "verify",
      challenge_token: "fictional-mobile-mfa-challenge-token",
      expires_in: 600,
    };
    fetcher.mockResolvedValueOnce(Response.json(result));
    const response = await proxyMobileRequest(
      request("auth/login", "POST", { Authorization: "" }),
      ["auth", "login"],
    );
    expect(await response.json()).toEqual(result);
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(fetcher.mock.calls[0][1]?.headers).not.toHaveProperty(
      "Authorization",
    );
  });

  it("requires the original idempotency key for intake writes", async () => {
    expect(
      (
        await proxyMobileRequest(request("conversation-intakes", "POST"), [
          "conversation-intakes",
        ])
      ).status,
    ).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
    fetcher.mockResolvedValueOnce(
      Response.json(
        { saved: true },
        { headers: { "Idempotent-Replayed": "true" } },
      ),
    );
    const response = await proxyMobileRequest(
      request("conversation-intakes", "POST", {
        "Idempotency-Key": "fictional-original-intake-key",
      }),
      ["conversation-intakes"],
    );
    expect(response.headers.get("Idempotent-Replayed")).toBe("true");
    expect(fetcher.mock.calls[0][1]?.headers).toHaveProperty(
      "Idempotency-Key",
      "fictional-original-intake-key",
    );
  });

  it("does not permit alternate methods or encoded paths", () => {
    expect(mobilePathAllowed("auth/login", "GET")).toBe(false);
    expect(mobilePathAllowed(`appointments/${id}/reschedule`, "DELETE")).toBe(
      false,
    );
    expect(mobilePathAllowed("appointments/%2e%2e/operations", "GET")).toBe(
      false,
    );
  });

  it("rejects upstream paths and credential-bearing origins", async () => {
    vi.stubEnv(
      "NEXT_PUBLIC_API_BASE_URL",
      "https://untrusted:fictional@api.hvacline.example/prefix",
    );
    expect(
      (await proxyMobileRequest(request("appointments"), ["appointments"]))
        .status,
    ).toBe(503);
    expect(fetcher).not.toHaveBeenCalled();
  });
});
