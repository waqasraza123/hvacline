import { websiteAsset } from "./assets";
import { fontIds, sectionIds, templateIds } from "./contracts";
import type { AgentConfiguration, ColorTokens, WebsiteAction, WebsiteAppearance, WebsiteConfiguration, WebsiteTemplate } from "./contracts";

type RecordValue = Record<string, unknown>;

function object(value: unknown, keys: readonly string[], path: string): RecordValue {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  const record = value as RecordValue;
  for (const key of Object.keys(record)) {
    if (!keys.includes(key)) throw new Error(`${path}.${key} is not supported`);
  }
  return record;
}

function text(value: unknown, path: string, maximum = 800): string {
  if (typeof value !== "string" || !value.trim() || value.length > maximum || /[\u0000-\u001f\u007f]/.test(value)) {
    throw new Error(`${path} must be nonempty text of at most ${maximum} characters`);
  }
  return value.trim();
}

function choice<const T extends readonly string[]>(value: unknown, options: T, path: string): T[number] {
  if (typeof value !== "string" || !options.includes(value)) throw new Error(`${path} is not supported`);
  return value as T[number];
}

function list<T>(value: unknown, path: string, parse: (item: unknown, path: string) => T, minimum = 0, maximum = 12): T[] {
  if (!Array.isArray(value) || value.length < minimum || value.length > maximum) throw new Error(`${path} requires ${minimum}–${maximum} entries`);
  return value.map((item: unknown, index) => parse(item, `${path}[${index}]`));
}

function asset(value: unknown, path: string): string {
  const id = text(value, path, 80);
  websiteAsset(id);
  return id;
}

function colors(value: unknown, path: string): ColorTokens {
  const keys = ["background", "surface", "foreground", "muted", "accent", "accentInk", "border"] as const;
  const row = object(value, keys, path);
  const color = (key: (typeof keys)[number]) => {
    if (typeof row[key] !== "string" || !/^#[a-f\d]{6}$/i.test(row[key])) throw new Error(`${path}.${key} must be a six-digit hex color`);
    return row[key];
  };
  return { background: color("background"), surface: color("surface"), foreground: color("foreground"), muted: color("muted"), accent: color("accent"), accentInk: color("accentInk"), border: color("border") };
}

function appearance(value: unknown, path: string): WebsiteAppearance {
  const row = object(value, ["light", "dark", "headingFont", "bodyFont", "spacing"], path);
  return {
    light: colors(row.light, `${path}.light`), dark: colors(row.dark, `${path}.dark`),
    headingFont: choice(row.headingFont, fontIds, `${path}.headingFont`),
    bodyFont: choice(row.bodyFont, fontIds, `${path}.bodyFont`),
    spacing: choice(row.spacing, ["compact", "balanced", "airy"], `${path}.spacing`),
  };
}

export function validateWebsiteUrl(value: unknown): string {
  const href = text(value, "URL", 500);
  if (/[\s\\]/.test(href) || /%(?:0[0-9a-f]|1[0-9a-f]|7f|2f|5c)/i.test(href)) throw new Error("URL contains unsafe characters");
  if (href.startsWith("/") && !href.startsWith("//")) {
    const parsed = new URL(href, "https://website.invalid");
    if (parsed.origin !== "https://website.invalid" || parsed.search || /(?:^|\/)\.{1,2}(?:\/|$)/.test(decodeURIComponent(href.split("#")[0]))) throw new Error("URL must be a safe local path without query parameters");
    return href;
  }
  const parsed = new URL(href);
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.port) throw new Error("External URLs must use HTTPS without credentials or a custom port");
  return href;
}

function action(value: unknown, path: string): WebsiteAction {
  const row = object(value, ["label", "destination"], path);
  const destination = object(row.destination, ["kind", "section", "href"], `${path}.destination`);
  const kind = choice(destination.kind, ["section", "url", "voice"], `${path}.destination.kind`);
  const label = text(row.label, `${path}.label`, 70);
  if (kind === "section") {
    if (destination.href !== undefined) throw new Error(`${path} section actions cannot contain URLs`);
    return { label, destination: { kind, section: choice(destination.section, sectionIds, `${path}.section`) } };
  }
  if (kind === "url") {
    if (destination.section !== undefined) throw new Error(`${path} URL actions cannot select sections`);
    return { label, destination: { kind, href: validateWebsiteUrl(destination.href) } };
  }
  if (destination.href !== undefined || destination.section !== undefined) throw new Error(`${path} voice actions cannot choose an agent or URL`);
  return { label, destination: { kind } };
}

function content(value: unknown, path: string) {
  const row = object(value, ["title", "description"], path);
  return { title: text(row.title, `${path}.title`, 140), description: text(row.description, `${path}.description`) };
}

export function validateWebsiteTemplate(value: unknown): WebsiteTemplate {
  const row = object(value, ["id", "layoutFamily", "supportedSections", "requiredSections", "themeTokens", "variants"], "template");
  const supported = list(row.supportedSections, "template.supportedSections", (item, path) => choice(item, sectionIds, path), 3);
  const required = list(row.requiredSections, "template.requiredSections", (item, path) => choice(item, sectionIds, path), 1);
  if (new Set(supported).size !== supported.length || new Set(required).size !== required.length || required.some((section) => !supported.includes(section))) throw new Error("Template sections must be unique and required sections must be supported");
  const variants = object(row.variants, ["button", "imagery"], "template.variants");
  return {
    id: choice(row.id, templateIds, "template.id"),
    layoutFamily: choice(row.layoutFamily, ["industrial-split", "editorial-mosaic", "calm-centered"], "template.layoutFamily"),
    supportedSections: supported, requiredSections: required, themeTokens: appearance(row.themeTokens, "template.themeTokens"),
    variants: { button: choice(variants.button, ["square", "outline", "pill"], "template.button"), imagery: choice(variants.imagery, ["blueprint", "editorial", "organic"], "template.imagery") },
  };
}

export function validateWebsiteConfiguration(value: unknown): WebsiteConfiguration {
  const row = object(value, ["slug", "templateId", "status", "industry", "designStyle", "summary", "brand", "appearance", "sections", "header", "hero", "actions", "services", "showcase", "story", "process", "voice", "faqs", "contact", "seo", "agentConfigurationRef"], "website");
  const slug = text(row.slug, "website.slug", 64);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error("website.slug must be a lowercase URL slug");
  const brand = object(row.brand, ["name", "tagline", "logo", "favicon"], "website.brand");
  const header = object(row.header, ["navigation"], "website.header");
  const hero = object(row.hero, ["eyebrow", "title", "description", "image", "imageCaption"], "website.hero");
  const actions = object(row.actions, ["primary", "secondary"], "website.actions");
  const story = object(row.story, ["title", "description", "eyebrow", "image"], "website.story");
  const voice = object(row.voice, ["title", "description", "examples"], "website.voice");
  const contact = object(row.contact, ["title", "description", "location", "hours", "email", "phone"], "website.contact");
  const seo = object(row.seo, ["title", "description"], "website.seo");
  const sections = list(row.sections, "website.sections", (item, path) => choice(item, sectionIds, path), 3);
  if (new Set(sections).size !== sections.length) throw new Error("website.sections cannot repeat");
  const navigation = list(header.navigation, "website.navigation", (item, path) => {
    const link = object(item, ["label", "section"], path);
    const section = choice(link.section, sectionIds, `${path}.section`);
    if (!sections.includes(section)) throw new Error(`${path} targets a missing section`);
    return { label: text(link.label, `${path}.label`, 40), section };
  }, 1, 5);
  const primary = action(actions.primary, "website.actions.primary");
  const secondary = action(actions.secondary, "website.actions.secondary");
  for (const cta of [primary, secondary]) {
    if (cta.destination.kind === "section" && !sections.includes(cta.destination.section)) throw new Error("Website action targets a missing section");
    if (cta.destination.kind === "voice" && !sections.includes("voice")) throw new Error("Voice actions require a voice section");
  }
  const email = contact.email === null ? null : text(contact.email, "website.contact.email", 200);
  const phone = contact.phone === null ? null : text(contact.phone, "website.contact.phone", 30);
  if (email && !/^[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i.test(email)) throw new Error("Invalid contact email");
  if (phone && !/^\+[1-9]\d{7,14}$/.test(phone)) throw new Error("Contact phone must use E.164 format");
  return {
    slug, templateId: choice(row.templateId, templateIds, "website.templateId"), status: choice(row.status, ["demo", "published"], "website.status"),
    industry: text(row.industry, "website.industry", 60), designStyle: text(row.designStyle, "website.designStyle", 60), summary: text(row.summary, "website.summary", 220),
    brand: { name: text(brand.name, "website.brand.name", 70), tagline: text(brand.tagline, "website.brand.tagline", 100), logo: asset(brand.logo, "website.logo"), favicon: asset(brand.favicon, "website.favicon") },
    appearance: appearance(row.appearance, "website.appearance"), sections, header: { navigation },
    hero: { eyebrow: text(hero.eyebrow, "website.hero.eyebrow", 90), title: text(hero.title, "website.hero.title", 160), description: text(hero.description, "website.hero.description"), image: asset(hero.image, "website.hero.image"), imageCaption: text(hero.imageCaption, "website.hero.imageCaption", 180) },
    actions: { primary, secondary },
    services: list(row.services, "website.services", content, 1, 6),
    showcase: list(row.showcase, "website.showcase", (item, path) => {
      const entry = object(item, ["title", "description", "image", "label"], path);
      return { title: text(entry.title, `${path}.title`, 140), description: text(entry.description, `${path}.description`), image: asset(entry.image, `${path}.image`), label: text(entry.label, `${path}.label`, 80) };
    }, 0, 4),
    story: { title: text(story.title, "website.story.title", 140), description: text(story.description, "website.story.description"), eyebrow: text(story.eyebrow, "website.story.eyebrow", 90), image: asset(story.image, "website.story.image") },
    process: list(row.process, "website.process", content, 1, 5),
    voice: { title: text(voice.title, "website.voice.title", 140), description: text(voice.description, "website.voice.description"), examples: list(voice.examples, "website.voice.examples", (item, path) => {
      const entry = object(item, ["role", "text"], path);
      return { role: choice(entry.role, ["visitor", "assistant"], `${path}.role`), text: text(entry.text, `${path}.text`, 500) };
    }, 2, 6) },
    faqs: list(row.faqs, "website.faqs", (item, path) => {
      const entry = object(item, ["question", "answer"], path);
      return { question: text(entry.question, `${path}.question`, 180), answer: text(entry.answer, `${path}.answer`) };
    }, 1, 8),
    contact: { title: text(contact.title, "website.contact.title", 140), description: text(contact.description, "website.contact.description"), location: text(contact.location, "website.contact.location", 160), hours: text(contact.hours, "website.contact.hours", 160), email, phone },
    seo: { title: text(seo.title, "website.seo.title", 120), description: text(seo.description, "website.seo.description", 240) },
    agentConfigurationRef: text(row.agentConfigurationRef, "website.agentConfigurationRef", 80),
  };
}

export function validateAgentConfiguration(value: unknown): AgentConfiguration {
  const row = object(value, ["id", "businessReference", "voiceAgentReference", "approvedKnowledge", "conversation", "capabilities"], "agent");
  const knowledge = object(row.approvedKnowledge, ["kind", "reference"], "agent.approvedKnowledge");
  const conversation = object(row.conversation, ["authentication", "modes", "memory"], "agent.conversation");
  const capabilities = object(row.capabilities, ["scheduling", "leadCapture", "crm"], "agent.capabilities");
  const provider = row.voiceAgentReference === null ? null : choice(row.voiceAgentReference, ["existing-server-hvac-provider"], "agent.voiceAgentReference");
  const authentication = choice(conversation.authentication, ["existing-customer-mfa", "unavailable"], "agent.authentication");
  const memory = choice(conversation.memory, ["existing-account-scoped", "disabled"], "agent.memory");
  const modes = list(conversation.modes, "agent.modes", (item, path) => choice(item, ["VOICE", "TEXT"], path), 0, 2);
  const scheduling = choice(capabilities.scheduling, ["existing-hvac", "preview-only"], "agent.scheduling");
  const leadCapture = choice(capabilities.leadCapture, ["existing-hvac", "preview-only"], "agent.leadCapture");
  const knowledgeKind = choice(knowledge.kind, ["business-approved", "static-demo"], "agent.knowledge.kind");
  if (new Set(modes).size !== modes.length) throw new Error("Agent modes must be unique");
  if (provider === null && (authentication !== "unavailable" || memory !== "disabled" || modes.length || scheduling !== "preview-only" || leadCapture !== "preview-only")) throw new Error("Unconfigured agents cannot enable sessions, memory or live tools");
  if (provider !== null && (authentication !== "existing-customer-mfa" || memory !== "existing-account-scoped" || !modes.includes("VOICE"))) throw new Error("Existing HVAC entry must preserve authenticated conversation controls");
  if ((provider === null && knowledgeKind !== "static-demo") || (provider !== null && knowledgeKind !== "business-approved")) throw new Error("Knowledge availability must match the agent binding");
  return {
    id: text(row.id, "agent.id", 80), businessReference: text(row.businessReference, "agent.businessReference", 80), voiceAgentReference: provider,
    approvedKnowledge: { kind: knowledgeKind, reference: text(knowledge.reference, "agent.knowledge.reference", 80) },
    conversation: { authentication, modes, memory }, capabilities: { scheduling, leadCapture, crm: choice(capabilities.crm, ["unavailable"], "agent.crm") },
  };
}

export function validateTemplateCompatibility(website: WebsiteConfiguration, template: WebsiteTemplate) {
  if (website.templateId !== template.id || website.sections.some((id) => !template.supportedSections.includes(id)) || template.requiredSections.some((id) => !website.sections.includes(id))) throw new Error(`Website ${website.slug} does not match its template sections`);
  if (website.sections.includes("showcase") && website.showcase.length === 0) throw new Error("Showcase sections need content");
}

export function freezeConfiguration<T>(value: T): T {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) freezeConfiguration(child);
    Object.freeze(value);
  }
  return value;
}
