import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./styles.css";
export const metadata: Metadata = {
  title: {
    default: "HVACLine AI — AI Phone Receptionist & Appointment Booking",
    template: "%s | HVACLine AI",
  },
  description:
    "An AI phone receptionist for U.S. HVAC service companies. Capture repair requests, check technician availability, book appointments, and route urgent calls.",
  openGraph: {
    title: "HVACLine AI",
    description:
      "The next job starts with a call. AI phone reception and scheduling for heating and air businesses.",
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
