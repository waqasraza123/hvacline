import "server-only";
import { demoWebsites } from "./catalog";
import { resolveVoicePresentation } from "./agents.server";
import type { ResolvedWebsite, WebsiteConfigurationSource } from "./contracts";
import { websiteTemplates } from "./templates";
import {
  freezeConfiguration,
  validateTemplateCompatibility,
  validateWebsiteConfiguration,
} from "./validation";

const staticWebsiteSource: WebsiteConfigurationSource = {
  async findBySlug(slug) {
    return demoWebsites.find((website) => website.slug === slug) ?? null;
  },
};

export async function resolveDemoWebsite(
  slug: string,
  voiceFeatureEnabled = false,
  source: WebsiteConfigurationSource = staticWebsiteSource,
): Promise<ResolvedWebsite | null> {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 64) return null;
  const stored = await source.findBySlug(slug);
  if (!stored) return null;
  const configuration = validateWebsiteConfiguration(stored);
  if (configuration.slug !== slug || configuration.status !== "demo")
    return null;
  const template = websiteTemplates[configuration.templateId];
  validateTemplateCompatibility(configuration, template);
  return freezeConfiguration({
    configuration,
    template,
    voice: resolveVoicePresentation(configuration, voiceFeatureEnabled),
  });
}
