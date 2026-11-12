import { describe, expect, it } from "vitest";
import { demoWebsites } from "./catalog";
import { websiteTemplates } from "./templates";
import { validateAgentConfiguration, validateTemplateCompatibility, validateWebsiteConfiguration, validateWebsiteTemplate, validateWebsiteUrl } from "./validation";

const website = () => structuredClone(demoWebsites[0]);
const previewAgent = () => ({
  id: "example-preview", businessReference: "fictional-example", voiceAgentReference: null,
  approvedKnowledge: { kind: "static-demo", reference: "example-content" },
  conversation: { authentication: "unavailable", modes: [], memory: "disabled" },
  capabilities: { scheduling: "preview-only", leadCapture: "preview-only", crm: "unavailable" },
});

describe("website configuration contracts", () => {
  it("validates each complete demo against its selected layout", () => {
    for (const configuration of demoWebsites) {
      const parsed = validateWebsiteConfiguration(configuration);
      expect(parsed).toEqual(configuration);
      expect(() => validateTemplateCompatibility(parsed, websiteTemplates[parsed.templateId])).not.toThrow();
    }
    expect(new Set(demoWebsites.map((site) => site.templateId)).size).toBe(3);
    expect(new Set(Object.values(websiteTemplates).map((template) => template.layoutFamily)).size).toBe(3);
  });

  it.each(["../hvac", "HVAC", "hvac/other", "hvac?agent_id=other", "__proto__", ""]) ("rejects invalid slug %s", (slug) => {
    expect(() => validateWebsiteConfiguration({ ...website(), slug })).toThrow();
  });

  it("rejects arbitrary agent IDs, unapproved assets, fonts and injected CSS", () => {
    const configuration = website();
    expect(() => validateWebsiteConfiguration({ ...configuration, agent_id: "another-provider-agent" })).toThrow(/not supported/);
    expect(() => validateWebsiteConfiguration({ ...configuration, brand: { ...configuration.brand, logo: "https://unapproved.example/image.svg" } })).toThrow(/not approved/);
    expect(() => validateWebsiteConfiguration({ ...configuration, appearance: { ...configuration.appearance, headingFont: "url(https://unapproved.example/font)" } })).toThrow();
    expect(() => validateWebsiteConfiguration({ ...configuration, appearance: { ...configuration.appearance, light: { ...configuration.appearance.light, accent: "red; background:url(x)" } } })).toThrow(/hex color/);
  });

  it("rejects duplicate or missing sections and invalid navigation", () => {
    const configuration = website();
    expect(() => validateWebsiteConfiguration({ ...configuration, sections: ["hero", "hero", "contact"] })).toThrow(/repeat/);
    expect(() => validateTemplateCompatibility({ ...configuration, sections: ["hero", "services", "contact"] }, websiteTemplates.industrial)).toThrow(/template sections/);
    expect(() => validateWebsiteConfiguration({ ...configuration, header: { navigation: [{ label: "Collection", section: "showcase" }] } })).toThrow(/missing section/);
    expect(() => validateWebsiteTemplate({ ...websiteTemplates.industrial, requiredSections: ["showcase"] })).toThrow(/must be supported/);
  });

  it("requires property content for an enabled showcase", () => {
    const configuration = { ...demoWebsites[1], showcase: [] };
    expect(() => validateTemplateCompatibility(configuration, websiteTemplates.editorial)).toThrow(/need content/);
  });

  it("prevents voice CTAs from selecting URLs or provider IDs", () => {
    const configuration = website();
    for (const destination of [{ kind: "voice", href: "/book?agent_id=other" }, { kind: "voice", agent_id: "other" }]) {
      expect(() => validateWebsiteConfiguration({ ...configuration, actions: { ...configuration.actions, primary: { label: "Connect", destination } } })).toThrow();
    }
  });

  it.each(["javascript:alert(1)", "data:text/html,test", "//other.example", "/book?business_id=other", "/%2e%2e/admin", "https://user:password@example.com", "http://example.com", "/\\example.com", "/%0abook"]) ("rejects unsafe URL %s", (url) => {
    expect(() => validateWebsiteUrl(url)).toThrow();
  });

  it("accepts normal local and HTTPS links", () => {
    expect(validateWebsiteUrl("/book")).toBe("/book");
    expect(validateWebsiteUrl("/#call-me")).toBe("/#call-me");
    expect(validateWebsiteUrl("https://example.com/contact")).toBe("https://example.com/contact");
  });
});

describe("agent configuration contracts", () => {
  it("keeps an unconfigured business preview-only", () => {
    expect(validateAgentConfiguration(previewAgent()).conversation.modes).toEqual([]);
    expect(() => validateAgentConfiguration({ ...previewAgent(), conversation: { authentication: "unavailable", modes: ["VOICE"], memory: "disabled" } })).toThrow(/Unconfigured/);
    expect(() => validateAgentConfiguration({ ...previewAgent(), capabilities: { scheduling: "existing-hvac", leadCapture: "preview-only", crm: "unavailable" } })).toThrow(/Unconfigured/);
    expect(() => validateAgentConfiguration({ ...previewAgent(), approvedKnowledge: { kind: "business-approved", reference: "other-business" } })).toThrow(/Knowledge/);
    expect(() => validateAgentConfiguration({ ...previewAgent(), apiKey: "should-never-be-config-content" })).toThrow(/not supported/);
    expect(() => validateAgentConfiguration({ ...previewAgent(), voiceAgentReference: "arbitrary-provider-agent" })).toThrow(/not supported/);
  });
});
