import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CUSTOMER_COOKIE, CUSTOMER_MFA_COOKIE } from "@/features/customer/server";
import { GET, POST } from "./route";

const cookieStore = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("next/headers", () => ({ cookies: async () => cookieStore }));

const fetcher = vi.fn<typeof fetch>();
const user = {
  id: "fictional-account-id",
  full_name: "Fictional Customer",
  email: "fictional@example.com",
};
const sessionToken = "fictional-session-token-for-account-tests";
const challengeToken = "fictional-limited-mfa-challenge-for-account-tests";
const portalSecret = "fictional-portal-secret-for-account-tests";

function request(action: string, origin = "https://hvacline.example") {
  return new NextRequest(`https://hvacline.example/api/account/${action}`, {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: "{}",
  });
}

function context(action: string) {
  return { params: Promise.resolve({ action }) };
}

beforeEach(() => {
  fetcher.mockReset();
  cookieStore.get.mockReset();
  vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.hvacline.example");
  vi.stubEnv("CUSTOMER_PORTAL_SECRET", portalSecret);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("customer account proxy", () => {
  it.each([
    ["signup", 201],
    ["login", 200],
  ] as const)("sets only a limited HttpOnly MFA cookie after %s", async (action, status) => {
    fetcher.mockResolvedValueOnce(
      Response.json(
        { mfa_required: true, next_action: "enroll", challenge_token: challengeToken, expires_in: 600 },
        { status },
      ),
    );

    const response = await POST(request(action), context(action));

    expect(response.status).toBe(status);
    expect(await response.json()).toEqual({ mfa_required: true, next_action: "enroll" });
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.cookies.get(CUSTOMER_MFA_COOKIE)).toMatchObject({
      value: challengeToken,
      httpOnly: true,
      sameSite: "strict",
      path: "/",
      maxAge: 600,
    });
    expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({ value: "", maxAge: 0 });
    expect(fetcher).toHaveBeenCalledWith(
      `https://api.hvacline.example/api/v1/customer/auth/${action}`,
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Customer-Portal-Key": portalSecret,
        }),
        cache: "no-store",
        redirect: "error",
      }),
    );
    expect(response.headers.get("X-Customer-Portal-Key")).toBeNull();
  });

  it.each([
    { session_token: "short" },
    { session_token: "x".repeat(129) },
    { session_token: `${sessionToken};unexpected=value` },
    { session_token: `${sessionToken}\n` },
    { expires_in: 0 },
    { expires_in: 28801 },
    { expires_in: 1.5 },
    { user: { id: user.id } },
  ])("rejects malformed sign-in data %j", async (override) => {
    fetcher.mockResolvedValueOnce(
      Response.json({
        user,
        mfa_verified: true,
        session_token: sessionToken,
        expires_in: 28800,
        ...override,
      }),
    );

    const response = await POST(request("mfa-verify"), context("mfa-verify"));

    expect(response.status).toBe(502);
    expect(response.cookies.get(CUSTOMER_COOKIE)).toBeUndefined();
    expect(await response.text()).not.toContain(sessionToken);
  });

  it("rejects password-only full sessions from an older backend", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ user, session_token: sessionToken, expires_in: 28800 }));
    const response = await POST(request("login"), context("login"));
    expect(response.status).toBe(502);
    expect(response.cookies.get(CUSTOMER_COOKIE)).toBeUndefined();
    expect(await response.text()).not.toContain(sessionToken);
  });

  it("creates a full session only after MFA and strips both bearer tokens", async () => {
    cookieStore.get.mockImplementation((name: string) => ({
      value: name === CUSTOMER_MFA_COOKIE ? challengeToken : sessionToken,
    }));
    const recoveryCodes = Array.from({ length: 10 }, (_, index) =>
      `${index.toString(16).padStart(8, "0")}-aaaaaaaa-bbbbbbbb-cccccccc`);
    fetcher.mockResolvedValueOnce(Response.json({
      user, session_token: sessionToken, expires_in: 28800, mfa_verified: true,
      recovery_codes: recoveryCodes,
    }));
    const response = await POST(request("mfa-verify"), context("mfa-verify"));
    expect(await response.json()).toEqual({ user, recovery_codes: recoveryCodes });
    expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({ value: sessionToken, httpOnly: true, maxAge: 28800 });
    expect(response.cookies.get(CUSTOMER_MFA_COOKIE)).toMatchObject({ value: "", maxAge: 0 });
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.hvacline.example/api/v1/customer/auth/mfa/verify",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: `Bearer ${challengeToken}` }) }),
    );
  });

  it("keeps recovery limited to authenticator replacement", async () => {
    fetcher.mockResolvedValueOnce(Response.json({
      mfa_required: true, next_action: "enroll", challenge_token: challengeToken, expires_in: 600,
    }));
    const response = await POST(request("mfa-recover"), context("mfa-recover"));
    expect(await response.json()).toEqual({ mfa_required: true, next_action: "enroll" });
    expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({ value: "", maxAge: 0 });
    expect(response.cookies.get(CUSTOMER_MFA_COOKIE)?.value).toBe(challengeToken);
  });

  it("never forwards the limited challenge as ordinary account authorization", async () => {
    cookieStore.get.mockImplementation((name: string) =>
      name === CUSTOMER_MFA_COOKIE ? { value: challengeToken } : undefined);
    fetcher.mockResolvedValueOnce(Response.json({ error: { message: "Sign in again." } }, { status: 401 }));
    const response = await GET(new NextRequest("https://hvacline.example/api/account/me"), context("me"));
    expect(response.status).toBe(401);
    const headers = fetcher.mock.calls[0][1]?.headers;
    expect(headers).not.toHaveProperty("Authorization");
  });

  it.each(["mfa-setup", "mfa-verify", "mfa-recover", "mfa-cancel"])(
    "rejects cross-origin %s before contacting the backend", async (action) => {
      const response = await POST(request(action, "https://another.example"), context(action));
      expect(response.status).toBe(403);
      expect(fetcher).not.toHaveBeenCalled();
    },
  );

  it("rejects cross-origin sign-in before contacting the backend", async () => {
    const response = await POST(
      request("login", "https://another.example"),
      context("login"),
    );

    expect(response.status).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
    expect(response.cookies.get(CUSTOMER_COOKIE)).toBeUndefined();
  });

  it("rejects a cross-site logout without clearing the session", async () => {
    const incoming = request("logout");
    incoming.headers.set("Sec-Fetch-Site", "cross-site");

    const response = await POST(incoming, context("logout"));

    expect(response.status).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
    expect(response.cookies.get(CUSTOMER_COOKIE)).toBeUndefined();
  });

  it("rejects actions outside the account allowlist", async () => {
    const response = await POST(request("admin"), context("admin"));

    expect(response.status).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("preserves rate-limit feedback without setting a session", async () => {
    fetcher.mockResolvedValueOnce(
      Response.json(
        { error: { message: "Too many attempts. Please try again later." } },
        { status: 429, headers: { "Retry-After": "900" } },
      ),
    );

    const response = await POST(request("login"), context("login"));

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("900");
    expect(response.cookies.get(CUSTOMER_COOKIE)).toBeUndefined();
  });

  it("returns only account fields from the current-session endpoint", async () => {
    cookieStore.get.mockReturnValue({ value: sessionToken });
    fetcher.mockResolvedValueOnce(
      Response.json({ ...user, session_token: sessionToken }),
    );

    const response = await GET(
      new NextRequest("https://hvacline.example/api/account/me"),
      context("me"),
    );

    expect(await response.json()).toEqual(user);
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.hvacline.example/api/v1/customer/auth/me",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${sessionToken}`,
        }),
      }),
    );
  });

  it("clears the browser cookie when backend logout fails", async () => {
    fetcher.mockRejectedValueOnce(new Error("backend unavailable"));

    const response = await POST(request("logout"), context("logout"));

    expect(response.status).toBe(204);
    expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({
      value: "",
      httpOnly: true,
      maxAge: 0,
    });
  });
});
