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
