import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { themeInitializationScript } from "@/components/theme-preference";
import { ThemeSync } from "@/components/theme-sync";
import "./styles.css";
export const metadata: Metadata = {
  title: {
    default: "HVACLine | Customizable AI Voice Agents for Business",
    template: "%s | HVACLine AI",
  },
  description:
    "Customizable AI voice agents for customer conversations, lead capture, and business workflows. Explore HVACLine’s HVAC voice and appointment-booking example.",
  openGraph: {
    title: "HVACLine | Customizable AI Voice Agents for Business",
    description:
      "Customizable AI voice agents for customer conversations, lead capture, and business workflows. Explore HVACLine’s HVAC voice and appointment-booking example.",
    type: "website",
  },
  icons: {
    icon: { url: "/icon.svg?v=2", type: "image/svg+xml", sizes: "any" },
    shortcut: "/icon.svg?v=2",
  },
};
export const viewport: Viewport = {
  themeColor: "#18181b",
};
export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{ __html: themeInitializationScript }}
        />
      </head>
      <body>
        <ThemeSync />
        {children}
      </body>
    </html>
  );
}
