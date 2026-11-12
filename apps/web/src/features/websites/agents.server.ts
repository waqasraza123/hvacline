import "server-only";
import type { AgentConfiguration, VoicePresentation, WebsiteConfiguration } from "./contracts";
import { freezeConfiguration, validateAgentConfiguration } from "./validation";

const agentBindings = freezeConfiguration([
  {
    websiteSlug: "hvac",
    configuration: validateAgentConfiguration({
      id: "hvac-existing-flow", businessReference: "existing-backend-business-resolution",
      voiceAgentReference: "existing-server-hvac-provider",
      approvedKnowledge: { kind: "business-approved", reference: "existing-agency-approved-faqs" },
      conversation: { authentication: "existing-customer-mfa", modes: ["VOICE", "TEXT"], memory: "existing-account-scoped" },
      capabilities: { scheduling: "existing-hvac", leadCapture: "existing-hvac", crm: "unavailable" },
    }),
  },
  ...[
    { websiteSlug: "real-estate", id: "estate-preview", businessReference: "fictional-alder-stone" },
    { websiteSlug: "appointments", id: "morrow-preview", businessReference: "fictional-morrow-studio" },
  ].map((binding) => ({
    websiteSlug: binding.websiteSlug,
    configuration: validateAgentConfiguration({
      id: binding.id, businessReference: binding.businessReference, voiceAgentReference: null,
      approvedKnowledge: { kind: "static-demo", reference: `${binding.websiteSlug}-catalog-content` },
      conversation: { authentication: "unavailable", modes: [], memory: "disabled" },
      capabilities: { scheduling: "preview-only", leadCapture: "preview-only", crm: "unavailable" },
    }),
  })),
]);

export function resolveWebsiteAgent(website: WebsiteConfiguration): AgentConfiguration {
  const binding = agentBindings.find((entry) => entry.configuration.id === website.agentConfigurationRef);
  if (!binding || binding.websiteSlug !== website.slug) throw new Error("Website has no authorized agent binding");
  return binding.configuration;
}

export function resolveVoicePresentation(website: WebsiteConfiguration, voiceFeatureEnabled: boolean): VoicePresentation {
  const agent = resolveWebsiteAgent(website);
  if (agent.voiceAgentReference !== null && voiceFeatureEnabled) {
    return {
      kind: "existing-hvac-entry", href: "/book",
      notice: "Continue to the existing HVACLine account workspace. Sign-in, consent and backend availability checks are required. Opening this link does not start a session.",
    };
  }
  return {
    kind: "preview",
    notice: agent.voiceAgentReference === null
      ? "Design preview only. No voice agent is connected to this business. No calls, inquiries or bookings are made here."
      : "Written preview only. Browser voice is not enabled for this deployment. Existing HVACLine booking remains available separately.",
  };
}
