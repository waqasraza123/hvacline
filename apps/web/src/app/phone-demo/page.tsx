import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PhoneDemoBoard } from "@/features/phone-demo/phone-demo-board";
import {
  parseDemoPhoneNumber,
  parsePublicEnvironment,
} from "@/lib/environment";

export const metadata: Metadata = {
  title: "Phone Receptionist | HVACLine AI",
  description:
    "An AI HVAC front desk for service requests and appointment booking.",
  robots: { index: false, follow: false },
};

export default function PhoneDemoPage() {
  const environment = parsePublicEnvironment(process.env);
  if (
    !environment.demoSandboxEnabled ||
    !process.env.NEXT_PUBLIC_DEMO_PHONE_NUMBER?.trim()
  ) {
    notFound();
  }
  const phoneNumber = parseDemoPhoneNumber(process.env);
  return (
    <PhoneDemoBoard
      apiBaseUrl={environment.apiBaseUrl}
      phoneNumber={phoneNumber}
    />
  );
}
