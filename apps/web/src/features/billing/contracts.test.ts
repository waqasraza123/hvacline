import { describe, expect, it, vi } from "vitest";
import {
  checkoutRedirect,
  draftCatalog,
  hours,
  money,
  parseCatalog,
} from "./contracts";

describe("maintenance package billing", () => {
  it("shares the package-hour catalog with the backend and keeps the preview unavailable for payment", () => {
    expect(draftCatalog.plans.map((plan) => plan.included_hours)).toEqual([
      3, 5, 10,
    ]);
    expect(draftCatalog.checkout_enabled).toBe(false);
    expect(draftCatalog.draft).toBe(true);
    expect(hours(90)).toBe("1.5");
    expect(money(7500)).toBe("$75");
  });
  it("only opens Stripe checkout and portal redirects", () => {
    const assign = vi.fn();
    vi.stubGlobal("window", { location: { assign } });
    try {
      checkoutRedirect(
        "https://checkout.stripe.com/c/pay/cs_test_example",
        "checkout",
      );
      expect(assign).toHaveBeenCalledTimes(1);
      for (const value of [
        "https://checkout.stripe.com.evil.test",
        "http://checkout.stripe.com",
        "https://user@checkout.stripe.com",
        "https://checkout.stripe.com:444/",
      ]) {
        expect(() => checkoutRedirect(value, "checkout")).toThrow();
      }
      expect(() =>
        checkoutRedirect(
          "https://billing.stripe.com/p/session/test",
          "checkout",
        ),
      ).toThrow();
    } finally {
      vi.unstubAllGlobals();
    }
  });
  it("rejects incomplete, duplicate and invalid package data", () => {
    expect(parseCatalog(draftCatalog)).toEqual(draftCatalog);
    expect(() => parseCatalog({ ...draftCatalog, plans: [] })).toThrow();
    expect(() =>
      parseCatalog({
        ...draftCatalog,
        plans: [
          draftCatalog.plans[0],
          draftCatalog.plans[0],
          draftCatalog.plans[2],
        ],
      }),
    ).toThrow();
    expect(() =>
      parseCatalog({ ...draftCatalog, checkout_enabled: "true" }),
    ).toThrow();
  });
});
