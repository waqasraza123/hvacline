import { afterEach, describe, expect, it, vi } from "vitest";
import { demoWebsites } from "./catalog";
import { publishedWebsite } from "./published.server";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
describe("persisted website source", () => {
  it("keeps the static demos independent while the platform is disabled", async () => {
    vi.stubEnv("WEBSITE_PLATFORM_ENABLED", "false");
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    expect(await publishedWebsite("studio")).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("loads published configuration without provider or business IDs in the request", async () => {
    vi.stubEnv("WEBSITE_PLATFORM_ENABLED", "true");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://backend.example");
    const configuration = {
      ...demoWebsites[2],
      slug: "studio",
      status: "published",
      agentConfigurationRef: "server-managed",
    };
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({
        configuration,
        voice_available: true,
        capabilities: { lead_capture: true },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const site = await publishedWebsite("studio");
    expect(site?.voice).toMatchObject({
      kind: "website-session",
      slug: "studio",
      leadCapture: true,
    });
    expect(fetcher.mock.calls[0][0]).toBe(
      "https://backend.example/api/v1/websites/studio",
    );
    expect(fetcher.mock.calls[0][1]).toMatchObject({
      cache: "no-store",
      redirect: "error",
    });
  });
  it("does not turn disabled or missing sites into a working HVAC fallback", async () => {
    vi.stubEnv("WEBSITE_PLATFORM_ENABLED", "true");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://backend.example");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    );
    expect(await publishedWebsite("missing")).toBeNull();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          configuration: {
            ...demoWebsites[1],
            status: "published",
            agentConfigurationRef: "server-managed",
          },
          voice_available: false,
          capabilities: { lead_capture: false },
        }),
      ),
    );
    expect((await publishedWebsite("real-estate"))?.voice.kind).toBe("preview");
  });
});
