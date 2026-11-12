import { describe, expect, it } from "vitest";
import { demoWebsites } from "./catalog";
import { newWebsiteConfiguration } from "./editor";
import { websiteTemplates } from "./templates";
import {
  validateTemplateCompatibility,
  validateWebsiteConfiguration,
} from "./validation";

describe("website editor defaults", () => {
  it("creates valid independent drafts for every structural template", () => {
    for (const id of ["industrial", "editorial", "calm"] as const) {
      const configuration = newWebsiteConfiguration(
        id,
        "owned-studio",
        "Owned Studio",
      );
      validateWebsiteConfiguration(configuration);
      validateTemplateCompatibility(configuration, websiteTemplates[id]);
      expect(configuration.brand.name).toBe("Owned Studio");
      expect(configuration.agentConfigurationRef).toBe("server-managed");
      expect(configuration.faqs[0].answer).not.toContain("fictional");
    }
    expect(demoWebsites[2].brand.name).toBe("Morrow Studio");
    expect(newWebsiteConfiguration("calm").appearance).not.toBe(
      demoWebsites[2].appearance,
    );
  });
  it("rejects unsafe changes before they can be saved", () => {
    const configuration = newWebsiteConfiguration("calm");
    expect(() =>
      validateWebsiteConfiguration({
        ...configuration,
        brand: {
          ...configuration.brand,
          logo: "https://external.example/upload.svg",
        },
      }),
    ).toThrow();
    expect(() =>
      validateWebsiteConfiguration({
        ...configuration,
        actions: {
          ...configuration.actions,
          primary: {
            label: "Connect",
            destination: { kind: "voice", agent_id: "foreign" },
          },
        },
      }),
    ).toThrow();
  });
});
