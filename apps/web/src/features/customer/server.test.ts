import { describe, expect, it, vi } from "vitest";
import { CUSTOMER_COOKIE, completeCustomerLogout } from "./server";

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

describe("completeCustomerLogout", () => {
  it.each([204, 401, 503])(
    "clears the local session when revocation returns %i",
    async (status) => {
      const response = await completeCustomerLogout(
        Promise.resolve(new Response(null, { status })),
      );

      expect(response.status).toBe(204);
      expect(response.headers.get("Cache-Control")).toBe("no-store");
      expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({
        value: "",
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        maxAge: 0,
      });
    },
  );

  it("clears the local session when revocation is unavailable", async () => {
    const response = await completeCustomerLogout(
      Promise.reject(new Error("backend unavailable")),
    );

    expect(response.status).toBe(204);
    expect(response.cookies.get(CUSTOMER_COOKIE)).toMatchObject({
      value: "",
      httpOnly: true,
      maxAge: 0,
    });
  });
});
