import Link from "next/link";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Pricing } from "@/features/billing/pricing";
import "../product.css";

export const metadata = { title: "Maintenance packages & extra hours" };

export default function PricingPage() {
  return (
    <div className="product-site">
      <header className="product-header product-container">
        <Brand />
        <nav className="product-nav" aria-label="Pricing navigation">
          <Link href="/">How Line works</Link>
          <Link href="/book">Book a visit</Link>
        </nav>
        <div className="product-page-actions">
          <ThemeToggle />
          <Link className="product-button button-small" href="/billing">
            My package ↗
          </Link>
        </div>
      </header>
      <main>
        <Pricing />
      </main>
      <footer className="product-footer product-container">
        <Brand />
        <p>Clear maintenance hours. More comfort at home.</p>
        <Link href="/billing">Manage my package</Link>
      </footer>
    </div>
  );
}
