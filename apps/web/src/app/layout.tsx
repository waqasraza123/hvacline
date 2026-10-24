import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";
export const metadata: Metadata = {
  title: {
    default: "HVACLine — Less waiting. More comfort.",
    template: "%s | HVACLine AI",
  },
  description:
    "Book your heating, cooling, installation or maintenance appointment with Line, your AI booking assistant. One conversation. A time that works for you.",
  openGraph: {
    title: "HVACLine AI",
    description:
      "Less waiting. More comfort. Your next HVAC appointment is a conversation away.",
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
