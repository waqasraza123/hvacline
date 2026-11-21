"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Brand } from "./brand";
import { ProductIcon } from "./product-icons";
import { ThemeToggle } from "./theme-toggle";
import styles from "./header-navigation.module.css";

const links = [
  {
    href: "/operations",
    label: "Dashboard",
    description: "Explore the dashboard demo",
  },
  { href: "/pricing", label: "Pricing", description: "Maintenance packages" },
  {
    href: "/ai-lead-recovery",
    label: "AI Recovery",
    description: "Try the interactive lead recovery demo",
  },
] as const;

export function HeaderNavigation() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const activeHref = links.find((link) => link.href === pathname)?.href;
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1121px)");
    const closeOnDesktop = () => {
      if (media.matches) setOpen(false);
    };
    media.addEventListener("change", closeOnDesktop);
    return () => media.removeEventListener("change", closeOnDesktop);
  }, []);
  return (
    <div className={styles.navigation}>
      <nav className={styles.desktop} aria-label="Main navigation">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            data-active={activeHref === link.href ? "true" : undefined}
            aria-current={activeHref === link.href ? "page" : undefined}
          >
            {activeHref === link.href && (
              <span className={styles.activeDot} aria-hidden="true" />
            )}
            {link.label}
          </Link>
        ))}
      </nav>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild>
          <button
            type="button"
            className={styles.menuButton}
            aria-label="Open navigation"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M4 7h16M4 12h16M4 17h10" />
            </svg>
          </button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className={styles.overlay} />
          <Dialog.Content className={`product-site ${styles.drawer}`}>
            <div className={styles.drawerTop}>
              <Brand />
              <Dialog.Close asChild>
                <button
                  type="button"
                  className={styles.menuButton}
                  aria-label="Close navigation"
                >
                  <ProductIcon name="close" />
                </button>
              </Dialog.Close>
            </div>
            <div className={styles.drawerTools}>
              <span>Display theme</span>
              <ThemeToggle />
            </div>
            <Dialog.Title className={styles.title}>
              Find your next step.
            </Dialog.Title>
            <Dialog.Description className={styles.description}>
              Explore AI lead recovery, view maintenance packages or open your
              workspace.
            </Dialog.Description>
            <nav className={styles.mobile} aria-label="Mobile navigation">
              {links.map((link, index) => (
                <Dialog.Close asChild key={link.href}>
                  <Link
                    href={link.href}
                    data-active={activeHref === link.href ? "true" : undefined}
                    aria-current={activeHref === link.href ? "page" : undefined}
                  >
                    <span className={styles.number}>0{index + 1}</span>
                    <span>
                      <strong>
                        {activeHref === link.href && (
                          <span
                            className={styles.activeDot}
                            aria-hidden="true"
                          />
                        )}
                        {link.label}
                      </strong>
                      <small>{link.description}</small>
                    </span>
                    <ProductIcon name="arrow" />
                  </Link>
                </Dialog.Close>
              ))}
            </nav>
            <Dialog.Close asChild>
              <Link className={styles.voiceLink} href="/book">
                <ProductIcon name="mic" />
                Try Voice Chat
                <ProductIcon name="arrow" />
              </Link>
            </Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
