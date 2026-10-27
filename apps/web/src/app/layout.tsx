import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./styles.css";
export const metadata: Metadata = {
  title: {
    default: "HVACLine | Turn Missed Calls into HVAC Bookings",
    template: "%s | HVACLine AI",
  },
  description:
    "Stop losing jobs to missed calls. HVACLine talks with homeowners, checks live appointment slots, and confirms HVAC bookings in one conversation.",
  openGraph: {
    title: "HVACLine | Turn Missed Calls into HVAC Bookings",
    description:
      "Stop losing jobs to missed calls. HVACLine talks with homeowners, checks live appointment slots, and confirms HVAC bookings in one conversation.",
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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
