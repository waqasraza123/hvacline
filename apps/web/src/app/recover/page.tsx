import { CustomerRecoveryBooking } from "@/features/recovery/customer-continuation";
import "../product.css";

export const metadata = {
  title: "Continue your HVAC booking",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function RecoveryBookingPage() {
  return <CustomerRecoveryBooking />;
}
