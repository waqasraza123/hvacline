import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { resolveDemoWebsite } from "./registry.server";
import { WebsiteRenderer } from "./renderer";
import { DemoGallery } from "./demo-gallery";

vi.mock("@/components/theme-toggle", () => ({ ThemeToggle: () => null }));
afterEach(() => vi.restoreAllMocks());

describe("multi-demo presentation", () => {
  it("shows an accessible gallery linking to all three real demo routes", () => {
    const html = renderToStaticMarkup(createElement(DemoGallery));
    expect(html).toContain("Explore Voice AI Demos");
    for (const slug of ["hvac", "real-estate", "appointments"]) {
      expect(html).toContain(`href="/demos/${slug}"`);
      expect(html).toContain(`id="demo-${slug}-title"`);
      expect(html).toContain(`aria-describedby="demo-${slug}-description"`);
    }
    expect(html).toContain("Illustrated template previews");
    expect(html).toContain("sizes=");
  });

  it("renders complete, distinct layouts with their own sections and artwork", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Demo rendering must not call a backend"));
    const pages = await Promise.all(["hvac", "real-estate", "appointments"].map(async (slug) => {
      const site = (await resolveDemoWebsite(slug, true))!;
      const html = renderToStaticMarkup(createElement(WebsiteRenderer, { site }));
      for (const section of site.configuration.sections) expect(html).toContain(`id="${section}"`);
      expect(html).toContain(site.configuration.hero.title.replaceAll("&", "&amp;"));
      expect(html).toContain("Written example");
      expect(html).not.toContain("existing-server-hvac-provider");
      expect(html).not.toContain("existing-backend-business-resolution");
      return html;
    }));
    expect(pages[0]).toContain("hvac-equipment.svg");
    expect(pages[0]).toContain('href="/book"');
    expect(pages[1]).toContain("courtyard-home.svg");
    expect(pages[1]).toContain("city-residence.svg");
    expect(pages[2]).toContain("calm-studio.svg");
    for (const html of pages.slice(1)) {
      expect(html).not.toContain('href="/book"');
      expect(html).not.toContain("<form");
      expect(html).not.toContain("<iframe");
      expect(html).toContain("No voice agent is connected");
    }
    expect(fetch).not.toHaveBeenCalled();
  });

  it("escapes configured text instead of treating it as executable markup", async () => {
    const site = (await resolveDemoWebsite("appointments"))!;
    const configured = {
      ...site,
      configuration: {
        ...site.configuration,
        hero: { ...site.configuration.hero, title: "<script>window.example = true</script>" },
      },
    };
    const html = renderToStaticMarkup(createElement(WebsiteRenderer, { site: configured }));
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>window.example");
  });
});
