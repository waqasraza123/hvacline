import { describe, expect, it } from "vitest";

import {
  EnvironmentValidationError,
  parseDemoPhoneNumber,
  parseHomepagePhoneCta,
  parsePublicEnvironment,
} from "./environment";

describe("homepage phone CTA release gate", () => {
  it("hides the phone CTA until live calling is explicitly verified", () => {
    expect(parseHomepagePhoneCta({})).toBeNull();
    expect(
      parseHomepagePhoneCta({
        HOMEPAGE_PHONE_NUMBER_E164: "+15550100100",
        TELNYX_INBOUND_CALLING_VERIFIED: "false",
      }),
    ).toBeNull();
  });

  it("uses the configured number for the visible label and dial link", () => {
    expect(
      parseHomepagePhoneCta({
        HOMEPAGE_PHONE_NUMBER_E164: "+15550100100",
        TELNYX_INBOUND_CALLING_VERIFIED: "true",
      }),
    ).toEqual({
      displayNumber: "+1 (555) 010-0100",
      href: "tel:+15550100100",
    });
  });

  it.each([undefined, "", "201-555-0100", "+442012345678", "javascript:alert(1)"])(
    "rejects missing or invalid phone configuration when enabling calling",
    (number) => {
      expect(() =>
        parseHomepagePhoneCta({
          HOMEPAGE_PHONE_NUMBER_E164: number,
          TELNYX_INBOUND_CALLING_VERIFIED: "true",
        }),
      ).toThrow("HOMEPAGE_PHONE_NUMBER_E164 must be a US E.164 number");
    },
  );

  it("rejects ambiguous verification flags", () => {
    expect(() =>
      parseHomepagePhoneCta({ TELNYX_INBOUND_CALLING_VERIFIED: "yes" }),
    ).toThrow("TELNYX_INBOUND_CALLING_VERIFIED must be true or false");
  });
});

describe("parsePublicEnvironment", () => {
  it("returns a normalized API URL", () => {
    expect(
      parsePublicEnvironment({
        NEXT_PUBLIC_API_BASE_URL: "https://api.example.com/",
      }),
    ).toEqual({
      apiBaseUrl: "https://api.example.com",
      conversationAiEnabled: false,
      demoSandboxEnabled: false,
    });
  });

  it("rejects a missing API URL", () => {
    expect(() => parsePublicEnvironment({})).toThrow(
      new EnvironmentValidationError("NEXT_PUBLIC_API_BASE_URL is required"),
    );
  });

  it("rejects unsupported URL protocols", () => {
    expect(() =>
      parsePublicEnvironment({ NEXT_PUBLIC_API_BASE_URL: "ftp://example.com" }),
    ).toThrow("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS");
  });

  it("parses the public conversation feature flag", () => {
    expect(
      parsePublicEnvironment({
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
        NEXT_PUBLIC_CONVERSATION_AI_ENABLED: "true",
      }).conversationAiEnabled,
    ).toBe(true);
  });

  it("rejects an invalid public conversation feature flag", () => {
    expect(() =>
      parsePublicEnvironment({
        NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
        NEXT_PUBLIC_CONVERSATION_AI_ENABLED: "yes",
      }),
    ).toThrow("NEXT_PUBLIC_CONVERSATION_AI_ENABLED must be true or false");
  });

  it("does not require phone configuration for browser routes", () => {
    expect(
      parsePublicEnvironment({
        NEXT_PUBLIC_API_BASE_URL: "https://api.example.com",
        NEXT_PUBLIC_DEMO_SANDBOX_ENABLED: "true",
        NEXT_PUBLIC_DEMO_PHONE_NUMBER: "555-0100",
      }).demoSandboxEnabled,
    ).toBe(true);
  });

  it("requires an E.164 number when parsing phone demo configuration", () => {
    expect(() =>
      parseDemoPhoneNumber({
        NEXT_PUBLIC_DEMO_PHONE_NUMBER: "555-0100",
      }),
    ).toThrow("NEXT_PUBLIC_DEMO_PHONE_NUMBER must use E.164 format");
  });

  it("parses the public phone demo configuration", () => {
    expect(
      parseDemoPhoneNumber({
        NEXT_PUBLIC_DEMO_PHONE_NUMBER: "+15550100100",
      }),
    ).toBe("+15550100100");
  });
});
