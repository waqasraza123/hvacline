import { NextRequest } from "next/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { handleWorkspace, WORKSPACE_COOKIE } from "./proxy";

const fetcher = vi.fn<typeof fetch>();
const id = "00000000-0000-4000-8000-000000000001";
beforeEach(() => {
  fetcher.mockReset(); vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com");
  vi.stubEnv("WORKSPACE_PORTAL_SECRET", "synthetic-staff-portal-key-at-least-32-characters");
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

function post(path: string, body: unknown, origin = "https://hvacline.example") {
  return new NextRequest(`https://hvacline.example/api/workspace/${path}`, { method: "POST", headers: { Origin: origin, "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

it("rejects cross-origin writes and paths outside the staff allowlist", async () => {
  expect((await handleWorkspace(post("auth/login", {}, "https://elsewhere.example"), "auth/login")).status).toBe(403);
  expect((await handleWorkspace(post("leads", {}), "leads")).status).toBe(404);
  expect((await handleWorkspace(new NextRequest("https://hvacline.example/api/workspace/bootstrap/businesses"), "bootstrap/businesses")).status).toBe(404);
  expect(fetcher).not.toHaveBeenCalled();
});

it("uses only the dedicated staff cookie and server-side portal key", async () => {
  fetcher.mockResolvedValue(Response.json({ calls: [], service_requests: [], handoffs: [], appointments: [] }));
  const path = `businesses/${id}/hvac/operations`;
  await handleWorkspace(new NextRequest(`https://hvacline.example/api/workspace/${path}`, { headers: { Cookie: `${WORKSPACE_COOKIE}=synthetic-staff-session; hvacline-session=customer-session`, Authorization: "Bearer untrusted-browser-value" } }), path);
  expect(fetcher).toHaveBeenCalledWith(`https://api.example.com/api/v1/workspace/${path}`, expect.objectContaining({
    headers: expect.objectContaining({ Authorization: "Bearer synthetic-staff-session", "X-Workspace-Portal-Key": "synthetic-staff-portal-key-at-least-32-characters" }), redirect: "error", cache: "no-store",
  }));
});

it("does not treat a customer cookie as staff identity", async () => {
  fetcher.mockResolvedValue(Response.json({ error: { message: "Staff sign in required" } }, { status: 401 }));
  await handleWorkspace(new NextRequest("https://hvacline.example/api/workspace/auth/me", { headers: { Cookie: "hvacline-session=customer-session" } }), "auth/me");
  const options = fetcher.mock.calls[0][1];
  expect(options?.headers).not.toHaveProperty("Authorization");
});

it("removes the session token from browser JSON after verified MFA", async () => {
  fetcher.mockResolvedValue(Response.json({ session_token: "s".repeat(43), expires_in: 28800, mfa_verified: true }));
  const response = await handleWorkspace(post("auth/login", { email: "staff@example.com", password: "synthetic password", code: "123456" }), "auth/login");
  expect(await response.json()).toEqual({ signed_in: true });
  expect(response.headers.get("set-cookie")).toContain(`${WORKSPACE_COOKIE}=`);
  expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  expect(response.headers.get("set-cookie")).toContain("SameSite=strict");
  expect(response.headers.get("Cache-Control")).toBe("no-store");
});

it("refuses to issue a staff cookie for an unverified MFA response", async () => {
  fetcher.mockResolvedValue(Response.json({ session_token: "s".repeat(43), expires_in: 28800, mfa_verified: false }));
  const response = await handleWorkspace(post("auth/login", {}), "auth/login");
  expect(response.status).toBe(502);
  expect(response.headers.get("set-cookie")).toBeNull();
});

it("keeps the platform-owner key out of forwarded creation JSON", async () => {
  fetcher.mockResolvedValue(Response.json({ id, replayed: false, invitation: null }));
  await handleWorkspace(post("bootstrap/create", { bootstrap_key: "synthetic-bootstrap-key-at-least-32-characters", name: "Fictional business" }), "bootstrap/create");
  const options = fetcher.mock.calls[0][1];
  expect(options?.headers).toHaveProperty("X-Workspace-Bootstrap-Key", "synthetic-bootstrap-key-at-least-32-characters");
  expect(JSON.parse(String(options?.body))).toEqual({ name: "Fictional business" });
});
