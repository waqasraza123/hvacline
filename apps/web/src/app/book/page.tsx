import Link from "next/link";
import { redirect } from "next/navigation";
import { Brand } from "@/components/brand";
import { CustomerBooking } from "@/features/customer/booking";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Book your appointment" };

export default async function BookPage() {
  const customer = await currentCustomer();
  if (customer.status === "anonymous") redirect("/login");
  if (customer.status !== "authenticated")
    return (
      <div className="customer-shell">
        <header className="product-header product-container">
          <Brand />
        </header>
        <main className="customer-empty product-container">
          <h1>We’ll be right back.</h1>
          <p>
            Your account is temporarily unavailable. Please try again shortly.
          </p>
          <Link className="product-button" href="/book">
            Try again
          </Link>
          <Link className="product-text-link" href="/login">
            Return to sign in
          </Link>
        </main>
      </div>
    );
  return (
    <CustomerBooking
      user={customer.user}
      voiceEnabled={process.env.NEXT_PUBLIC_CONVERSATION_AI_ENABLED === "true"}
    />
  );
}
