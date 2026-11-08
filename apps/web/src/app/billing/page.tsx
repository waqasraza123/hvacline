import Link from "next/link";
import { redirect } from "next/navigation";
import { Brand } from "@/components/brand";
import { AccountAvatar } from "@/components/account-avatar";
import { ThemeToggle } from "@/components/theme-toggle";
import { BillingDashboard } from "@/features/billing/dashboard";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "My maintenance package" };

export default async function BillingPage() {
  const customer = await currentCustomer();
  if (customer.status === "anonymous") redirect("/login?intent=billing");
  return (
    <div className="product-site">
      <header className="product-header product-container">
        <Brand />
        <nav className="product-nav" aria-label="Account navigation">
          <Link href="/book">My appointments</Link>
          <Link href="/pricing">Packages</Link>
        </nav>
        <div className="product-page-actions">
          <ThemeToggle />
          {customer.status === "authenticated" && (
            <AccountAvatar fullName={customer.user.full_name} />
          )}
          <Link className="product-button button-small" href="/book">
            Book a visit ↗
          </Link>
        </div>
      </header>
      {customer.status === "authenticated" ? (
        <BillingDashboard accountId={customer.user.id} />
      ) : (
        <main className="product-container" style={{ paddingBlock: "4rem" }}>
          <h1>Your account is temporarily unavailable.</h1>
          <p>Please retry to load your package securely.</p>
          <Link className="product-button" href="/billing">
            Try again
          </Link>
        </main>
      )}
    </div>
  );
}
