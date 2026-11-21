import type { WebsiteConfiguration } from "./contracts";
import { websiteTemplates } from "./templates";
import {
  freezeConfiguration,
  validateTemplateCompatibility,
  validateWebsiteConfiguration,
} from "./validation";

const configurations: readonly WebsiteConfiguration[] = [
  {
    slug: "hvac",
    templateId: "industrial",
    status: "demo",
    industry: "HVAC services",
    designStyle: "Industrial / bold",
    summary:
      "A hard-working digital front desk. Strong type, equipment-inspired visuals and a clear route to HVAC service.",
    brand: {
      name: "HVACLine AI",
      tagline: "Keep the next job moving.",
      logo: "hvac-mark",
      favicon: "hvac-mark",
    },
    appearance: websiteTemplates.industrial.themeTokens,
    sections: ["hero", "services", "process", "voice", "faq", "contact"],
    header: {
      navigation: [
        { label: "Services", section: "services" },
        { label: "How it works", section: "process" },
        { label: "The receptionist", section: "voice" },
      ],
    },
    hero: {
      eyebrow: "HEATING. COOLING. HANDLED.",
      title: "Good service starts before the truck arrives.",
      description:
        "An AI front desk for the calls that come in while your team is on the job. Clear questions. Useful details. A better next step.",
      image: "hvac-equipment",
      imageCaption: "Illustrated HVAC service scenario · example website",
    },
    actions: {
      primary: {
        label: "Meet the receptionist",
        destination: { kind: "voice" },
      },
      secondary: {
        label: "Explore our services",
        destination: { kind: "section", section: "services" },
      },
    },
    services: [
      {
        title: "Cooling repair",
        description:
          "Warm air, unusual cycling or a system that will not start. Capture the issue and request a service visit.",
      },
      {
        title: "Heating repair",
        description:
          "Help the team understand the heating concern. Safety-related requests go to human attention.",
      },
      {
        title: "New systems",
        description:
          "Start a conversation about replacing equipment or planning an installation consultation.",
      },
      {
        title: "Seasonal maintenance",
        description:
          "Make room for the routine visits that keep heating and cooling on the calendar.",
      },
    ],
    showcase: [],
    story: {
      eyebrow: "BUILT AROUND THE JOB",
      title: "A useful first conversation.",
      description:
        "Clear service details help a team decide what comes next. The receptionist does not diagnose equipment or invent repair prices.",
      image: "hvac-equipment",
    },
    process: [
      {
        title: "Tell us what is happening",
        description:
          "Share the issue, service address and the kind of help you need.",
      },
      {
        title: "Review the next step",
        description:
          "The existing HVACLine flow checks service areas and configured availability.",
      },
      {
        title: "Confirm before booking",
        description:
          "An appointment is only booked after your explicit confirmation and a successful save.",
      },
    ],
    voice: {
      title: "The first call. Without the phone tag.",
      description:
        "Explore an example of service intake below, or continue to the existing HVACLine account workspace. Voice and Text availability are checked there.",
      examples: [
        {
          role: "visitor",
          text: "My air conditioner is running, but the house is not cooling.",
        },
        {
          role: "assistant",
          text: "I can help collect the details for a service request. What is the service ZIP code?",
        },
        { role: "visitor", text: "Can I choose a time before I confirm?" },
        {
          role: "assistant",
          text: "In the connected booking flow, you review an available time and explicitly confirm before anything is booked.",
        },
      ],
    },
    faqs: [
      {
        question: "Is this a live HVAC business website?",
        answer:
          "This is an illustrative HVACLine template. The service content is example content. Its account link continues to the existing HVACLine flow, whose business and availability are resolved by the backend.",
      },
      {
        question: "Does the receptionist diagnose equipment?",
        answer:
          "No. It collects service details, uses approved business information and routes safety concerns to staff. It does not invent diagnoses or prices.",
      },
      {
        question: "Will browsing this demo book an appointment?",
        answer:
          "No. This page does not connect a voice session or save a booking. The existing signed-in flow has its own consent, availability and confirmation requirements.",
      },
    ],
    contact: {
      title: "Give every service request a clear next step.",
      description:
        "Open the existing HVACLine workspace to review the available conversation and booking options. Sign-in and consent are required.",
      location: "U.S. HVAC service businesses · example content",
      hours: "Availability follows the connected business calendar",
      email: null,
      phone: null,
    },
    seo: {
      title: "HVACLine AI — Industrial Voice AI Website Demo",
      description:
        "Explore an industrial HVAC website template with bold orange branding, service intake and an entry to the existing HVACLine workspace.",
    },
    agentConfigurationRef: "hvac-existing-flow",
  },
  {
    slug: "real-estate",
    templateId: "editorial",
    status: "demo",
    industry: "Real estate",
    designStyle: "Editorial / luxury",
    summary:
      "Considered homes. Considered conversations. A warm editorial experience for a fictional property advisory.",
    brand: {
      name: "Alder & Stone",
      tagline: "Homes with a point of view.",
      logo: "estate-mark",
      favicon: "estate-mark",
    },
    appearance: websiteTemplates.editorial.themeTokens,
    sections: [
      "hero",
      "showcase",
      "story",
      "voice",
      "services",
      "faq",
      "contact",
    ],
    header: {
      navigation: [
        { label: "The collection", section: "showcase" },
        { label: "Our approach", section: "story" },
        { label: "Inquire", section: "voice" },
      ],
    },
    hero: {
      eyebrow: "A MORE CONSIDERED WAY HOME",
      title: "Places to live. Space to belong.",
      description:
        "Thoughtful spaces, individual stories, and a conversation that begins with you. Discover a quieter approach to finding your next home.",
      image: "courtyard-home",
      imageCaption:
        "The Courtyard House · architectural illustration, not a listing",
    },
    actions: {
      primary: { label: "Begin an inquiry", destination: { kind: "voice" } },
      secondary: {
        label: "Discover the collection",
        destination: { kind: "section", section: "showcase" },
      },
    },
    services: [
      {
        title: "Finding your next home",
        description:
          "Begin with the places, routines and details that matter to your everyday life.",
      },
      {
        title: "Considering a move",
        description:
          "Outline what you are looking for before arranging a conversation with an adviser.",
      },
      {
        title: "A more personal inquiry",
        description:
          "Bring your questions about an illustrated property or the consultation process.",
      },
    ],
    showcase: [
      {
        title: "The Courtyard House",
        description:
          "Quiet geometry, warm stone and a garden at the centre of daily life.",
        image: "courtyard-home",
        label: "Illustrated concept / garden residence",
      },
      {
        title: "The Window House",
        description:
          "Tall openings, tactile brick and room to pause above the rhythm of the city.",
        image: "city-residence",
        label: "Illustrated concept / city residence",
      },
    ],
    story: {
      eyebrow: "THE ALDER & STONE APPROACH",
      title: "A home is more than its particulars.",
      description:
        "It is the light across a room. A familiar walk. The feeling of arriving. Our fictional advisory is built around a simple idea: understand the person before discussing the property.",
      image: "city-residence",
    },
    process: [
      {
        title: "Share your priorities",
        description:
          "Start with your location, preferred home style and the questions you want to discuss.",
      },
      {
        title: "Arrange a conversation",
        description:
          "A separately configured adviser would review the inquiry before confirming a consultation.",
      },
    ],
    voice: {
      title: "A good conversation opens doors.",
      description:
        "A written example of a future property inquiry assistant. This fictional advisory has no connected agent, and no inquiries or consultations are submitted.",
      examples: [
        {
          role: "visitor",
          text: "I am drawn to the courtyard home. Could I ask about arranging a viewing?",
        },
        {
          role: "assistant",
          text: "In a connected advisory, I would collect which home interests you and your preferred consultation times for the team to review.",
        },
        { role: "visitor", text: "Can I book a viewing here?" },
        {
          role: "assistant",
          text: "This is a design preview. There are no active listings, appointments or live property agents on this demo.",
        },
      ],
    },
    faqs: [
      {
        question: "Are these properties for sale?",
        answer:
          "No. Both homes are original architectural illustrations for a fictional brand. There are no live listings, asking prices or properties offered for sale.",
      },
      {
        question: "Can I speak to an agent or arrange a viewing?",
        answer:
          "Not through this preview. Alder & Stone has no connected voice agent or business calendar. The inquiry section shows an example conversation only.",
      },
      {
        question: "What would a connected assistant help with?",
        answer:
          "A future approved real estate assistant could collect inquiry preferences, answer business-approved questions and request a consultation. Availability and business permissions would need separate configuration.",
      },
    ],
    contact: {
      title: "Your next chapter begins with a conversation.",
      description:
        "Explore the inquiry preview to see how a more personal first conversation could feel. No information is collected or sent.",
      location: "Alder & Stone · fictional property advisory",
      hours: "Consultations are not available in this preview",
      email: null,
      phone: null,
    },
    seo: {
      title: "Alder & Stone — Editorial Real Estate Website Demo",
      description:
        "A fictional luxury property advisory: warm serif typography, architectural illustrations and an explicitly non-live voice inquiry preview.",
    },
    agentConfigurationRef: "estate-preview",
  },
  {
    slug: "appointments",
    templateId: "calm",
    status: "demo",
    industry: "Appointment-based services",
    designStyle: "Calm / minimal",
    summary:
      "A softer welcome for a busy day. An airy, sage-toned front desk for a fictional creative consultation studio.",
    brand: {
      name: "Morrow Studio",
      tagline: "A little room for your next idea.",
      logo: "calm-mark",
      favicon: "calm-mark",
    },
    appearance: websiteTemplates.calm.themeTokens,
    sections: ["hero", "services", "process", "voice", "faq", "contact"],
    header: {
      navigation: [
        { label: "Ways to meet", section: "services" },
        { label: "What to expect", section: "process" },
        { label: "Questions", section: "faq" },
      ],
    },
    hero: {
      eyebrow: "A WARM WELCOME. A CLEAR NEXT STEP.",
      title: "Make space for what comes next.",
      description:
        "A friendly first conversation for your next creative project. Explore the studio, find your kind of session, and see how a simpler front desk could work.",
      image: "calm-studio",
      imageCaption:
        "An illustrated Morrow Studio · a fictional appointment-based business",
    },
    actions: {
      primary: {
        label: "Meet your front desk",
        destination: { kind: "voice" },
      },
      secondary: {
        label: "Find your kind of session",
        destination: { kind: "section", section: "services" },
      },
    },
    services: [
      {
        title: "A first conversation",
        description:
          "A relaxed introduction to your idea, the questions on your mind, and what you would like to explore.",
      },
      {
        title: "A focused planning session",
        description:
          "Bring a project you are ready to think through, one considered decision at a time.",
      },
      {
        title: "A follow-up",
        description:
          "Return to an existing conversation and decide what the next step could look like.",
      },
    ],
    showcase: [],
    story: {
      eyebrow: "LESS ADMIN. MORE ATTENTION.",
      title: "A front desk with room to listen.",
      description:
        "This fictional studio is an example of an appointment-based business. All sessions and scheduling shown here are illustrative.",
      image: "calm-studio",
    },
    process: [
      {
        title: "Start with a question",
        description:
          "Tell the front desk the kind of session or information you are looking for.",
      },
      {
        title: "Find a suitable next step",
        description:
          "A connected assistant would use the studio’s approved session details and calendar.",
      },
      {
        title: "Review, then confirm",
        description:
          "You would always review the details before an appointment is saved. Nothing is booked in this preview.",
      },
    ],
    voice: {
      title: "Ask a little. Get a clearer next step.",
      description:
        "Read an example of a calm studio welcome. Morrow has no connected agent or calendar; this preview does not listen, collect information or book sessions.",
      examples: [
        {
          role: "visitor",
          text: "I have an idea for a project but do not know which session to choose.",
        },
        {
          role: "assistant",
          text: "A first conversation is designed to explore your idea and questions. A connected studio could help you find an available time.",
        },
        { role: "visitor", text: "Is an appointment being held for me?" },
        {
          role: "assistant",
          text: "No. This is a written preview, and no session or reservation has been created.",
        },
      ],
    },
    faqs: [
      {
        question: "Can I book a session today?",
        answer:
          "This is a fictional studio website demo. No business calendar or voice agent is connected, so appointments cannot be held or booked.",
      },
      {
        question: "Do I need to use my microphone?",
        answer:
          "No. This page only shows a written example conversation. It does not request microphone permission or start a call.",
      },
      {
        question: "Is my conversation being remembered?",
        answer:
          "No conversation is running on this demo. It does not create a customer account, collect inquiry details or store customer memory.",
      },
    ],
    contact: {
      title: "There is room for your next idea.",
      description:
        "Take a look at the front desk preview, at your own pace. No account, microphone or personal details needed.",
      location: "Morrow Studio · fictional creative consultation studio",
      hours: "Illustrative sessions · no live appointment availability",
      email: null,
      phone: null,
    },
    seo: {
      title: "Morrow Studio — Calm Appointment Website Demo",
      description:
        "A fictional appointment studio with sage colors, spacious design and a clearly labeled, non-live conversational receptionist preview.",
    },
    agentConfigurationRef: "morrow-preview",
  },
];

export const demoWebsites = freezeConfiguration(
  configurations.map((value) => {
    const configuration = validateWebsiteConfiguration(value);
    validateTemplateCompatibility(
      configuration,
      websiteTemplates[configuration.templateId],
    );
    return configuration;
  }),
);

if (
  new Set(demoWebsites.map((site) => site.slug)).size !== demoWebsites.length
) {
  throw new Error("Website slugs must be unique");
}
