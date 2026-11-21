import "server-only";
import { cache } from "react";
import type { ResolvedWebsite } from "./contracts";
import { websiteTemplates } from "./templates";
import {
  freezeConfiguration,
  validateTemplateCompatibility,
  validateWebsiteConfiguration,
} from "./validation";

export const publishedWebsite = cache(
  async (slug: string): Promise<ResolvedWebsite | null> => {
    if (
      process.env.WEBSITE_PLATFORM_ENABLED !== "true" ||
      !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ||
      slug.length > 64
    )
      return null;
    const base = new URL(process.env.NEXT_PUBLIC_API_BASE_URL ?? "");
    if (
      !(
        ["https:"].includes(base.protocol) ||
        (process.env.NODE_ENV !== "production" &&
          base.protocol === "http:" &&
          ["localhost", "127.0.0.1"].includes(base.hostname))
      ) ||
      base.username ||
      base.password ||
      base.search ||
      base.hash
    )
      throw new Error("Website backend configuration is unavailable");
    const response = await fetch(
      `${base.toString().replace(/\/$/, "")}/api/v1/websites/${slug}`,
      {
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(10000),
      },
    );
    if (response.status === 404) return null;
    if (!response.ok) throw new Error("Website is temporarily unavailable");
    const data: unknown = await response.json();
    if (
      !data ||
      typeof data !== "object" ||
      !("configuration" in data) ||
      !("voice_available" in data) ||
      typeof data.voice_available !== "boolean" ||
      !("capabilities" in data) ||
      !data.capabilities ||
      typeof data.capabilities !== "object" ||
      !("lead_capture" in data.capabilities) ||
      typeof data.capabilities.lead_capture !== "boolean"
    )
      throw new Error("Invalid website response");
    const configuration = validateWebsiteConfiguration(data.configuration);
    if (configuration.slug !== slug || configuration.status !== "published")
      return null;
    const template = websiteTemplates[configuration.templateId];
    validateTemplateCompatibility(configuration, template);
    return freezeConfiguration({
      configuration,
      template,
      voice: data.voice_available
        ? {
            kind: "website-session",
            slug,
            leadCapture: data.capabilities.lead_capture,
            notice:
              "Voice and Text use this website’s configured agent. Sign-in and explicit consent are required. Appointments and memory are unavailable in this conversation.",
          }
        : {
            kind: "preview",
            notice:
              "This website’s voice agent is not available. No conversation, inquiry or booking has started.",
          },
    });
  },
);
