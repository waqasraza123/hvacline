export const templateIds = ["industrial", "editorial", "calm"] as const;
export const sectionIds = ["hero", "services", "showcase", "story", "process", "voice", "faq", "contact"] as const;
export const fontIds = ["system", "industrial", "serif", "humanist"] as const;

export type TemplateId = (typeof templateIds)[number];
export type SectionId = (typeof sectionIds)[number];
export type FontId = (typeof fontIds)[number];
export type ColorTokens = Readonly<{
  background: string;
  surface: string;
  foreground: string;
  muted: string;
  accent: string;
  accentInk: string;
  border: string;
}>;
export type WebsiteAppearance = Readonly<{
  light: ColorTokens;
  dark: ColorTokens;
  headingFont: FontId;
  bodyFont: FontId;
  spacing: "compact" | "balanced" | "airy";
}>;
export type WebsiteTemplate = Readonly<{
  id: TemplateId;
  layoutFamily: "industrial-split" | "editorial-mosaic" | "calm-centered";
  supportedSections: readonly SectionId[];
  requiredSections: readonly SectionId[];
  themeTokens: WebsiteAppearance;
  variants: Readonly<{
    button: "square" | "outline" | "pill";
    imagery: "blueprint" | "editorial" | "organic";
  }>;
}>;
export type WebsiteAction = Readonly<{
  label: string;
  destination:
    | Readonly<{ kind: "section"; section: SectionId }>
    | Readonly<{ kind: "url"; href: string }>
    | Readonly<{ kind: "voice" }>;
}>;
export type ContentItem = Readonly<{
  title: string;
  description: string;
}>;
export type WebsiteConfiguration = Readonly<{
  slug: string;
  templateId: TemplateId;
  status: "demo" | "published";
  industry: string;
  designStyle: string;
  summary: string;
  brand: Readonly<{ name: string; tagline: string; logo: string; favicon: string }>;
  appearance: WebsiteAppearance;
  sections: readonly SectionId[];
  header: Readonly<{ navigation: readonly Readonly<{ label: string; section: SectionId }>[] }>;
  hero: Readonly<{ eyebrow: string; title: string; description: string; image: string; imageCaption: string }>;
  actions: Readonly<{ primary: WebsiteAction; secondary: WebsiteAction }>;
  services: readonly ContentItem[];
  showcase: readonly Readonly<ContentItem & { image: string; label: string }>[];
  story: Readonly<ContentItem & { eyebrow: string; image: string }>;
  process: readonly ContentItem[];
  voice: Readonly<ContentItem & {
    examples: readonly Readonly<{ role: "visitor" | "assistant"; text: string }>[];
  }>;
  faqs: readonly Readonly<{ question: string; answer: string }>[];
  contact: Readonly<{ title: string; description: string; location: string; hours: string; email: string | null; phone: string | null }>;
  seo: Readonly<{ title: string; description: string }>;
  agentConfigurationRef: string;
}>;

export type AgentConfiguration = Readonly<{
  id: string;
  businessReference: string;
  voiceAgentReference: "existing-server-hvac-provider" | null;
  approvedKnowledge: Readonly<{ kind: "business-approved" | "static-demo"; reference: string }>;
  conversation: Readonly<{
    authentication: "existing-customer-mfa" | "unavailable";
    modes: readonly ("VOICE" | "TEXT")[];
    memory: "existing-account-scoped" | "disabled";
  }>;
  capabilities: Readonly<{
    scheduling: "existing-hvac" | "preview-only";
    leadCapture: "existing-hvac" | "preview-only";
    crm: "unavailable";
  }>;
}>;

export type VoicePresentation =
  | Readonly<{ kind: "existing-hvac-entry"; href: "/book"; notice: string }>
  | Readonly<{ kind: "preview"; notice: string }>;

export type ResolvedWebsite = Readonly<{
  configuration: WebsiteConfiguration;
  template: WebsiteTemplate;
  voice: VoicePresentation;
}>;

export interface WebsiteConfigurationSource {
  findBySlug(slug: string): Promise<WebsiteConfiguration | null>;
}
