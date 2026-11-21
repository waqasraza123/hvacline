import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

const backend = vi.hoisted(() => vi.fn());
vi.mock("@/features/customer/server", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/customer/server")
  >("@/features/customer/server");
  return { ...actual, customerBackend: backend };
});
beforeEach(() => {
  backend.mockReset();
  backend.mockResolvedValue(
    Response.json({ session_id: "synthetic" }, { status: 201 }),
  );
});

function request(origin = "https://web.example", body = "{}") {
  return new NextRequest(
    "https://web.example/api/websites/studio/conversation-sessions",
    {
      method: "POST",
      headers: {
        Origin: origin,
        "Content-Type": "application/json",
        "X-Agency-Id": "foreign",
        "X-Agent-Id": "foreign",
      },
      body,
    },
  );
}

describe("website customer proxy", () => {
  it("binds the request to its site path and reuses server-side customer authentication", async () => {
    const response = await POST(request(), {
      params: Promise.resolve({
        slug: "studio",
        path: ["conversation-sessions"],
      }),
    });
    expect(response.status).toBe(201);
    expect(backend).toHaveBeenCalledWith(
      "websites/studio/conversation-sessions",
      "POST",
      "{}",
      undefined,
    );
  });
  it("rejects cross-origin mutations and unsupported tools", async () => {
    expect(
      (
        await POST(request("https://other.example"), {
          params: Promise.resolve({
            slug: "studio",
            path: ["conversation-sessions"],
          }),
        })
      ).status,
    ).toBe(403);
    expect(
      (
        await POST(request(), {
          params: Promise.resolve({ slug: "studio", path: ["memory"] }),
        })
      ).status,
    ).toBe(404);
    expect(
      (
        await POST(request(), {
          params: Promise.resolve({
            slug: "studio",
            path: [
              "conversation-sessions",
              "00000000-0000-4000-8000-000000000001",
              "booking",
            ],
          }),
        })
      ).status,
    ).toBe(404);
    expect(
      (
        await POST(request(), {
          params: Promise.resolve({
            slug: "../other",
            path: ["conversation-sessions"],
          }),
        })
      ).status,
    ).toBe(404);
    expect(backend).not.toHaveBeenCalled();
  });
});
