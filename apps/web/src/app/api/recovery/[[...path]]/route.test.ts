import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET, POST } from "./route";

const fetcher = vi.fn<typeof fetch>();
const capability = `${"a".repeat(32)}.${"b".repeat(64)}`;
const context = (path: string[] = []) => ({ params: Promise.resolve({ path }) });
function request(path: string, body: unknown, origin = "https://www.example.test") {
  return new NextRequest(`https://www.example.test/api/recovery/${path}`, {
    method: "POST", headers: { Origin: origin, "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
}

beforeEach(() => {
  fetcher.mockReset(); vi.stubGlobal("fetch", fetcher);
  vi.stubEnv("NODE_ENV", "test");
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
});
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("recovery continuation proxy", () => {
  it("exchanges a fragment capability only after backend validation into an HttpOnly scoped cookie", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ status: "ACTIVE", confirmed: false }));
    const response = await POST(request("exchange", { token: capability }), context(["exchange"]));
    expect(response.status).toBe(200);
    expect(response.cookies.get("hvacline-recovery")).toMatchObject({ httpOnly: true, secure: true, sameSite: "strict", path: "/api/recovery" });
    expect(fetcher.mock.calls[0][0]).toBe("https://api.example.test/api/v1/recovery/continuation");
    expect(fetcher.mock.calls[0][1]).toMatchObject({ redirect: "error", cache: "no-store", headers: { Authorization: `Bearer ${capability}` } });
    expect(await response.text()).not.toContain(capability);
  });

  it("rejects foreign origins before exchanging or booking", async () => {
    expect((await POST(request("exchange", { token: capability }, "https://untrusted.example"), context(["exchange"]))).status).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("does not create a cookie for a revoked or expired grant", async () => {
    fetcher.mockResolvedValueOnce(Response.json({ error: { message: "Expired" } }, { status: 403 }));
    const response = await POST(request("exchange", { token: capability }), context(["exchange"]));
    expect(response.status).toBe(403);
    expect(response.cookies.get("hvacline-recovery")).toBeUndefined();
  });

  it("rejects arbitrary backend routes and missing capabilities", async () => {
    expect((await POST(request("admin/settings", {}), context(["admin", "settings"]))).status).toBe(404);
    expect((await GET(new NextRequest("https://www.example.test/api/recovery"), context())).status).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("forwards confirmation once and preserves unknown failures without retrying", async () => {
    fetcher.mockRejectedValueOnce(new Error("private provider diagnostic"));
    const incoming = new NextRequest("https://www.example.test/api/recovery/confirm", {
      method: "POST", headers: { Origin: "https://www.example.test", "Content-Type": "application/json", Cookie: `hvacline-recovery=${capability}` },
      body: JSON.stringify({ expected_row_version: 4, nonce: "synthetic-nonce", explicit_confirmation: true }),
    });
    const response = await POST(incoming, context(["confirm"]));
    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain("private provider diagnostic");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
