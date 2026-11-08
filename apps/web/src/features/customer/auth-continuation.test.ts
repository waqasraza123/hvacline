import { describe, expect, it } from "vitest";
import {
  authPageHref,
  authReturnHref,
  parseAuthIntent,
} from "./auth-continuation";

describe("callback sign-in continuation", () => {
  it("returns a package purchase to billing after login, signup and MFA", () => {
    const intent = parseAuthIntent("billing");
    expect(authPageHref("/login", intent)).toBe("/login?intent=billing");
    expect(authPageHref("/signup", intent)).toBe("/signup?intent=billing");
    expect(authPageHref("/mfa", intent)).toBe("/mfa?intent=billing");
    expect(authReturnHref(intent)).toBe("/billing");
  });
  it("preserves the callback intent through login, signup and MFA", () => {
    const intent = parseAuthIntent("demo-call");
    expect(authPageHref("/login", intent)).toBe("/login?intent=demo-call");
    expect(authPageHref("/signup", intent)).toBe("/signup?intent=demo-call");
    expect(authPageHref("/mfa", intent)).toBe("/mfa?intent=demo-call");
    expect(authReturnHref(intent)).toBe("/?demo_call=1");
  });

  it.each([
    undefined,
    null,
    "",
    "https://attacker.example",
    "//attacker.example",
    "/operations",
    ["demo-call", "https://attacker.example"],
  ])("ignores unapproved continuation input %j", (value) => {
    const intent = parseAuthIntent(value);
    expect(authReturnHref(intent)).toBe("/book");
    expect(authPageHref("/login", intent)).toBe("/login");
    expect(authPageHref("/signup", intent)).toBe("/signup");
    expect(authPageHref("/mfa", intent)).toBe("/mfa");
  });
});
