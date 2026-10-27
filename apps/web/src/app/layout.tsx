import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";
export const metadata: Metadata = {
  title: {
    default: "HVACLine | AI Voice Receptionist for HVAC Businesses",
    template: "%s | HVACLine AI",
  },
  description:
    "Stop losing jobs to missed calls. HVACLine talks with homeowners, checks live appointment slots, and confirms HVAC bookings in one conversation.",
  openGraph: {
    title: "HVACLine | AI Voice Receptionist for HVAC Businesses",
    description:
      "Stop losing jobs to missed calls. HVACLine talks with homeowners, checks live appointment slots, and confirms HVAC bookings in one conversation.",
    type: "website",
  },
  icons: { icon: "/icon.svg" },
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
