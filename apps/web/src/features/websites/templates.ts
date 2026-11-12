import type { TemplateId, WebsiteTemplate } from "./contracts";
import { freezeConfiguration, validateWebsiteTemplate } from "./validation";

export const websiteTemplates: Readonly<Record<TemplateId, WebsiteTemplate>> = freezeConfiguration({
  industrial: validateWebsiteTemplate({
    id: "industrial",
    layoutFamily: "industrial-split",
    supportedSections: ["hero", "services", "process", "voice", "faq", "contact"],
    requiredSections: ["hero", "voice", "contact"],
    themeTokens: {
      light: { background: "#f4f2ed", surface: "#ffffff", foreground: "#202022", muted: "#605d58", accent: "#f97316", accentInk: "#202022", border: "#d8d5ce" },
      dark: { background: "#161618", surface: "#222225", foreground: "#f5f2eb", muted: "#b9b5ad", accent: "#f97316", accentInk: "#18181b", border: "#414144" },
      headingFont: "industrial", bodyFont: "system", spacing: "balanced",
    },
    variants: { button: "square", imagery: "blueprint" },
  }),
  editorial: validateWebsiteTemplate({
    id: "editorial",
    layoutFamily: "editorial-mosaic",
    supportedSections: ["hero", "showcase", "story", "services", "voice", "faq", "contact"],
    requiredSections: ["hero", "showcase", "voice", "contact"],
    themeTokens: {
      light: { background: "#f5f0e7", surface: "#ece4d8", foreground: "#352e29", muted: "#6d635a", accent: "#684637", accentInk: "#fff9ed", border: "#d4c7b7" },
      dark: { background: "#24211e", surface: "#302b26", foreground: "#f3e9d9", muted: "#bfb2a3", accent: "#d2b49b", accentInk: "#28221d", border: "#52483e" },
      headingFont: "serif", bodyFont: "system", spacing: "airy",
    },
    variants: { button: "outline", imagery: "editorial" },
  }),
  calm: validateWebsiteTemplate({
    id: "calm",
    layoutFamily: "calm-centered",
    supportedSections: ["hero", "services", "process", "voice", "faq", "contact"],
    requiredSections: ["hero", "voice", "contact"],
    themeTokens: {
      light: { background: "#fbfbf7", surface: "#edf1e9", foreground: "#293b32", muted: "#59685e", accent: "#3d5c49", accentInk: "#ffffff", border: "#d7dfd3" },
      dark: { background: "#19221d", surface: "#243129", foreground: "#edf2e9", muted: "#b4c1b3", accent: "#bad0b6", accentInk: "#1d2d22", border: "#405345" },
      headingFont: "humanist", bodyFont: "humanist", spacing: "airy",
    },
    variants: { button: "pill", imagery: "organic" },
  }),
});
