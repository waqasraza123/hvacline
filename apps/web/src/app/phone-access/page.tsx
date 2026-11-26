import Link from "next/link";
import { redirect } from "next/navigation";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { PhoneAccessPanel } from "@/features/customer/phone-access";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Telephone account access", robots: { index: false, follow: false } };

export default async function PhoneAccessPage() {
  const customer = await currentCustomer();
  if (customer.status === "anonymous") redirect("/login?intent=phone-access");
  return <div className="customer-shell">
    <header className="product-header product-container"><Brand /><ThemeToggle /><Link href="/book">Back to my account</Link></header>
    <main className="product-container">
      {customer.status !== "authenticated" ? <section className="customer-empty"><h1>Your account is unavailable</h1><p>Try again before approving telephone access.</p><Link className="product-button" href="/phone-access">Try again</Link></section>
        : process.env.PHONE_ACCOUNT_ACCESS_ENABLED === "true" ? <PhoneAccessPanel />
          : <section className="customer-empty"><h1>Telephone access is unavailable</h1><p>Contact the business for help with your appointments.</p></section>}
    </main>
  </div>;
}
