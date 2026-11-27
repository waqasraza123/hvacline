import type { ComponentProps } from "react";
import type { ProductIcon } from "@/components/product-icons";

export const navigationGroups = ["Workspace", "AI Configuration", "Business"] as const;

export const sections = [
  { key: "overview", label: "Overview", icon: "home", group: "Workspace" },
  { key: "calls", label: "Calls & conversations", icon: "phone", group: "Workspace" },
  { key: "requests", label: "Leads & requests", icon: "chat", group: "Workspace" },
  { key: "bookings", label: "Appointments", icon: "calendar", group: "Workspace" },
  { key: "handoffs", label: "Follow-up", icon: "clock", group: "Workspace" },
  { key: "recovery", label: "AI Lead Recovery", icon: "phone", group: "Workspace" },
  { key: "multilingual", label: "Voice & languages", icon: "languages", group: "AI Configuration" },
  { key: "knowledge", label: "Knowledge base", icon: "shield", group: "AI Configuration" },
  { key: "receptionist", label: "Agent settings", icon: "mic", group: "AI Configuration" },
  { key: "browser voice", label: "Browser voice", icon: "mic", group: "AI Configuration" },
  { key: "scheduling", label: "Scheduling", icon: "calendar", group: "Business" },
  { key: "integrations", label: "GoHighLevel", icon: "shield", group: "Business" },
  { key: "maintenance hours", label: "Maintenance hours", icon: "clock", group: "Business" },
  { key: "websites", label: "Websites", icon: "home", group: "Business" },
] as const satisfies ReadonlyArray<{
  key: string;
  label: string;
  icon: ComponentProps<typeof ProductIcon>["name"];
  group: (typeof navigationGroups)[number];
}>;

export type OperationsSection = (typeof sections)[number]["key"];


const sectionPaths: Record<OperationsSection, string> = {
  overview: "", calls: "calls", requests: "requests", bookings: "appointments",
  handoffs: "follow-up", recovery: "recovery", multilingual: "voice-languages",
  knowledge: "knowledge", receptionist: "agent-settings", "browser voice": "browser-voice",
  scheduling: "scheduling", integrations: "integrations/gohighlevel",
  "maintenance hours": "maintenance-hours", websites: "websites",
};

export const subpages = [
  { section: "handoffs", key: "queue", label: "Follow-up queue" },
  { section: "handoffs", key: "alerts", label: "Staff email alerts" },
  { section: "receptionist", key: "general", label: "General" },
  { section: "receptionist", key: "voice", label: "Voice & languages" },
  { section: "scheduling", key: "calendars", label: "Calendar connections" },
  { section: "scheduling", key: "rules", label: "Availability & teams" },
] as const satisfies ReadonlyArray<{ section: OperationsSection; key: string; label: string }>;

export type OperationsSubpage = (typeof subpages)[number]["key"];
export type OperationsDestination = { section: OperationsSection; subpage?: OperationsSubpage };

export function operationsHref(section: OperationsSection, subpage?: OperationsSubpage) {
  const path = sectionPaths[section];
  const base = path ? `/dashboard/${path}` : "/dashboard";
  return subpage && subpages.some((item) => item.section === section && item.key === subpage)
    ? `${base}/${subpage}` : base;
}

export function resolveOperationsPath(pathname: string): OperationsDestination | null {
  const path = pathname.replace(/\/+$/, "");
  for (const item of sections) {
    if (operationsHref(item.key) === path) return { section: item.key };
  }
  for (const item of subpages) {
    if (operationsHref(item.section, item.key) === path) {
      return { section: item.section, subpage: item.key };
    }
  }
  return null;
}
