import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AuthenticatorSetup } from "./authenticator-setup";
import { parseMfaSetup } from "./mfa-setup";

const secret = "A".repeat(32);
const query = new URLSearchParams({
  secret,
  issuer: "HVACLine AI",
  algorithm: "SHA1",
  digits: "6",
  period: "30",
});
const setup = {
  secret,
  otpauth_uri: `otpauth://totp/HVACLine%20AI%3Afictional%40example.test?${query}`,
};

describe("authenticator QR setup", () => {
  it("uses the backend provisioning URI and preserves the manual key", () => {
    expect(parseMfaSetup(setup)).toEqual({
      secret,
      otpauthUri: setup.otpauth_uri,
    });
    const html = renderToStaticMarkup(
      <AuthenticatorSetup setup={parseMfaSetup(setup)} />,
    );
    expect(html).toContain("<svg");
    expect(html).toContain("<path");
    expect(html).toContain("Scan to add HVACLine AI to your authenticator");
    expect(html).toContain("<details");
    expect(html).toContain(secret);
    expect(html).not.toContain("<img");
    expect(html).not.toContain(setup.otpauth_uri);
  });

  it.each([
    null,
    { secret },
    { ...setup, secret: "B".repeat(32) },
    { ...setup, otpauth_uri: "not a URI" },
    { ...setup, otpauth_uri: setup.otpauth_uri.replace("otpauth:", "https:") },
    { ...setup, otpauth_uri: setup.otpauth_uri.replace("totp/", "hotp/") },
    { ...setup, otpauth_uri: `${setup.otpauth_uri}&secret=${secret}` },
    { ...setup, otpauth_uri: `${setup.otpauth_uri}&digits=8` },
    {
      ...setup,
      otpauth_uri: setup.otpauth_uri.replace("digits=6", "digits=8"),
    },
    {
      ...setup,
      otpauth_uri: setup.otpauth_uri.replace("period=30", "period=60"),
    },
    {
      ...setup,
      otpauth_uri: setup.otpauth_uri.replace(
        "algorithm=SHA1",
        "algorithm=SHA256",
      ),
    },
    {
      ...setup,
      otpauth_uri: setup.otpauth_uri.replace(
        "issuer=HVACLine+AI",
        "issuer=Other",
      ),
    },
  ])(
    "rejects invalid or inconsistent provisioning without echoing credentials",
    (value) => {
      expect(() => parseMfaSetup(value)).toThrow(
        "Authenticator setup could not be loaded. Sign in again.",
      );
    },
  );
});
