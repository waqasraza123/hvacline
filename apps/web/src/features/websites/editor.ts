import { demoWebsites } from "./catalog";
import type { TemplateId, WebsiteConfiguration } from "./contracts";

export function newWebsiteConfiguration(
  templateId: TemplateId,
  slug = "my-website",
  brandName = "Your business",
): WebsiteConfiguration {
  const baseline = demoWebsites.find(
    (website) => website.templateId === templateId,
  );
  if (!baseline) throw new Error("Template is not available");
  return {
    ...structuredClone(baseline),
    slug,
    status: "demo",
    agentConfigurationRef: "server-managed",
    brand: { ...baseline.brand, name: brandName },
    hero: { ...baseline.hero, imageCaption: "Illustrative website artwork" },
    voice: {
      ...baseline.voice,
      description:
        "Choose a conversation mode when this business’s agent is available. Sign-in and explicit consent are required; opening this website does not start a session.",
    },
    contact: {
      ...baseline.contact,
      title: "A clear next step starts with a conversation.",
      description:
        "Use the receptionist when available to ask approved business questions or request human follow-up. No appointment is booked by the conversation.",
      location: "Business location",
      hours: "Contact the business for availability",
      email: null,
      phone: null,
    },
    faqs: [
      {
        question: "Does opening this page start a call?",
        answer:
          "No. Choose Voice or Text, sign in and accept the required consent before starting a conversation.",
      },
      {
        question: "Does the receptionist book appointments?",
        answer:
          "Appointment booking is not enabled in this website’s conversation. A confirmed inquiry requests human follow-up; it is not an appointment confirmation.",
      },
      {
        question: "What information can the assistant use?",
        answer:
          "The assistant’s business knowledge is selected by the website owner. Customer memory is disabled for this website’s conversations.",
      },
    ],
    seo: { title: brandName, description: baseline.summary },
  };
}
