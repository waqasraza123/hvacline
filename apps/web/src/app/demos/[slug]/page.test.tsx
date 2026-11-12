import { describe, expect, it, vi } from "vitest";
import DemoWebsitePage, { generateMetadata, generateStaticParams } from "./page";

vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("DEMO_NOT_FOUND"); } }));

describe("demo App Router entry", () => {
  it("generates direct routes and independent metadata for all sites", async () => {
    const params = generateStaticParams();
    expect(params).toEqual([{ slug: "hvac" }, { slug: "real-estate" }, { slug: "appointments" }]);
    const titles = new Set<string>();
    for (const route of params) {
      const metadata = await generateMetadata({ params: Promise.resolve(route) });
      expect(metadata.title).toHaveProperty("absolute");
      expect(metadata.icons).toHaveProperty("icon");
      expect(metadata.robots).toMatchObject({ index: false });
      titles.add(JSON.stringify(metadata.title));
      expect(await DemoWebsitePage({ params: Promise.resolve(route) })).toBeTruthy();
    }
    expect(titles.size).toBe(3);
  });

  it("returns not-found for unknown pages and their metadata", async () => {
    await expect(DemoWebsitePage({ params: Promise.resolve({ slug: "missing" }) })).rejects.toThrow("DEMO_NOT_FOUND");
    await expect(generateMetadata({ params: Promise.resolve({ slug: "missing" }) })).rejects.toThrow("DEMO_NOT_FOUND");
  });
});
