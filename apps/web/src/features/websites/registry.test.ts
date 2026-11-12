import { describe, expect, it } from "vitest";
import { demoWebsites } from "./catalog";
import { resolveWebsiteAgent } from "./agents.server";
import { resolveDemoWebsite } from "./registry.server";

describe("demo website resolution", () => {
  it.each(["hvac", "real-estate", "appointments"])(
    "resolves %s from the shared source",
    async (slug) => {
      const site = await resolveDemoWebsite(slug);
      expect(site?.configuration.slug).toBe(slug);
      expect(site?.template.id).toBe(site?.configuration.templateId);
    },
  );

  it.each([
    "unknown",
    "constructor",
    "__proto__",
    "../hvac",
    "HVAC",
    "hvac?agent_id=other",
  ])("does not resolve %s", async (slug) => {
    expect(await resolveDemoWebsite(slug, true)).toBeNull();
  });

  it("does not allow a selected site to choose another site's agent", () => {
    const estate = demoWebsites.find((site) => site.slug === "real-estate")!;
    expect(() =>
      resolveWebsiteAgent({
        ...estate,
        agentConfigurationRef: "hvac-existing-flow",
      }),
    ).toThrow(/authorized agent binding/);
    expect(() =>
      resolveWebsiteAgent({ ...estate, agentConfigurationRef: "unknown" }),
    ).toThrow(/authorized agent binding/);
  });

  it("never enables the HVAC provider for the other businesses", async () => {
    for (const slug of ["real-estate", "appointments"]) {
      const site = (await resolveDemoWebsite(slug, true))!;
      expect(site.voice.kind).toBe("preview");
      const agent = resolveWebsiteAgent(site.configuration);
      expect(agent.voiceAgentReference).toBeNull();
      expect(agent.conversation.memory).toBe("disabled");
      expect(agent.approvedKnowledge.kind).toBe("static-demo");
    }
    expect((await resolveDemoWebsite("hvac", true))?.voice).toMatchObject({
      kind: "existing-hvac-entry",
      href: "/book",
    });
    expect((await resolveDemoWebsite("hvac", false))?.voice.kind).toBe(
      "preview",
    );
  });

  it("keeps per-site content immutable and independent", async () => {
    const hvac = (await resolveDemoWebsite("hvac"))!;
    const estate = (await resolveDemoWebsite("real-estate"))!;
    expect(Object.isFrozen(hvac.configuration.appearance.light)).toBe(true);
    expect(hvac.configuration.appearance).not.toBe(
      estate.configuration.appearance,
    );
    expect(hvac.configuration.faqs).not.toBe(estate.configuration.faqs);
    expect(hvac.configuration.faqs[0].answer).not.toEqual(
      estate.configuration.faqs[0].answer,
    );
  });

  it("accepts a future configuration source without changing the renderer", async () => {
    const configuration = demoWebsites[0];
    const source = {
      async findBySlug() {
        return structuredClone(configuration);
      },
    };
    expect(
      (await resolveDemoWebsite("hvac", false, source))?.configuration.brand
        .name,
    ).toBe("HVACLine AI");
    expect(await resolveDemoWebsite("real-estate", false, source)).toBeNull();
    expect(
      await resolveDemoWebsite("hvac", false, {
        async findBySlug() {
          return { ...configuration, status: "published" };
        },
      }),
    ).toBeNull();
  });
});
