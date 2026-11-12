"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import type { ComponentProps, ReactNode } from "react";
import { Brand } from "@/components/brand";
import { ProductIcon } from "@/components/product-icons";
import { ThemeToggle } from "@/components/theme-toggle";
import styles from "./dashboard.module.css";

const sections = [
  { key: "websites", label: "Websites", icon: "home", group: "Manage" },
  { key: "overview", label: "Overview", icon: "home", group: "Workspace" },
  {
    key: "requests",
    label: "Service requests",
    icon: "chat",
    group: "Workspace",
  },
  {
    key: "bookings",
    label: "Appointments",
    icon: "calendar",
    group: "Workspace",
  },
  { key: "calls", label: "Calls", icon: "phone", group: "Workspace" },
  { key: "handoffs", label: "Follow-up", icon: "clock", group: "Workspace" },
  { key: "scheduling", label: "Scheduling", icon: "calendar", group: "Manage" },
  { key: "receptionist", label: "Receptionist", icon: "mic", group: "Manage" },
  {
    key: "knowledge",
    label: "Knowledge base",
    icon: "shield",
    group: "Manage",
  },
  {
    key: "maintenance hours",
    label: "Maintenance hours",
    icon: "clock",
    group: "Manage",
  },
  {
    key: "browser voice",
    label: "Browser voice",
    icon: "mic",
    group: "Manage",
  },
] as const satisfies ReadonlyArray<{
  key: string;
  label: string;
  icon: ComponentProps<typeof ProductIcon>["name"];
  group: string;
}>;

export type OperationsSection = (typeof sections)[number]["key"];

export function DashboardShell({
  section,
  onSelect,
  connected,
  busy,
  demo,
  conversationAiEnabled,
  onRefresh,
  children,
}: {
  section: OperationsSection;
  onSelect: (section: OperationsSection) => void;
  connected: boolean;
  busy: boolean;
  demo: boolean;
  conversationAiEnabled: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mainId = useId();
  const sidebarId = useId();
  const label = sections.find((item) => item.key === section)?.label;

  useEffect(() => {
    if (!mobileOpen) return;
    const media = window.matchMedia("(min-width: 1024px)");
    const closeOnDesktop = () => {
      if (media.matches) setMobileOpen(false);
    };
    media.addEventListener("change", closeOnDesktop);
    return () => media.removeEventListener("change", closeOnDesktop);
  }, [mobileOpen]);

  function navigation() {
    return (
      <nav aria-label="Operations sections" className={styles.navigation}>
        {["Workspace", "Manage"].map((group) => (
          <div key={group} className={styles.navGroup}>
            <p className={styles.groupLabel}>{group}</p>
            <ul>
              {sections
                .filter((item) => item.group === group)
                .filter(
                  (item) =>
                    item.key !== "browser voice" || conversationAiEnabled,
                )
                .map((item) => (
                  <li key={item.key}>
                    <button
                      type="button"
                      className={styles.navItem}
                      aria-current={section === item.key ? "page" : undefined}
                      aria-label={item.label}
                      title={item.label}
                      disabled={!connected || busy}
                      onClick={() => {
                        onSelect(item.key);
                        setMobileOpen(false);
                      }}
                    >
                      <ProductIcon name={item.icon} />
                      <span className={styles.navLabel}>{item.label}</span>
                    </button>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </nav>
    );
  }

  return (
    <div
      className={`${styles.theme} ${styles.shell} ${collapsed ? styles.collapsed : ""}`}
    >
      <a href={`#${mainId}`} className={styles.skipLink}>
        Skip to workspace
      </a>
      <aside
        id={sidebarId}
        className={styles.desktopSidebar}
        aria-label="Workspace navigation"
      >
        <div className={styles.sidebarBrand}>
          <Brand />
        </div>
        {navigation()}
        <div className={styles.sidebarFooter}>
          <ProductIcon name="shield" />
          <div className={styles.navLabel}>
            <strong>Your service workspace</strong>
            <p>Keep the next job moving.</p>
          </div>
        </div>
      </aside>
      <div className={styles.workspace}>
        <header className={styles.header}>
          <div className={styles.headerStart}>
            <button
              type="button"
              className={`${styles.iconButton} ${styles.desktopToggle}`}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-expanded={!collapsed}
              aria-controls={sidebarId}
              onClick={() => setCollapsed(!collapsed)}
            >
              <MenuIcon />
            </button>
            <Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}>
              <Dialog.Trigger asChild>
                <button
                  type="button"
                  className={`${styles.iconButton} ${styles.mobileToggle}`}
                  aria-label="Open workspace navigation"
                >
                  <MenuIcon />
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className={styles.overlay} />
                <Dialog.Content className={`${styles.theme} ${styles.drawer}`}>
                  <div className={styles.drawerHeading}>
                    <Brand />
                    <Dialog.Close asChild>
                      <button
                        type="button"
                        className={styles.iconButton}
                        aria-label="Close navigation"
                      >
                        <ProductIcon name="close" />
                      </button>
                    </Dialog.Close>
                  </div>
                  <Dialog.Title className={styles.srOnly}>
                    Workspace navigation
                  </Dialog.Title>
                  <Dialog.Description className={styles.srOnly}>
                    Choose a section of your HVAC service workspace.
                  </Dialog.Description>
                  {navigation()}
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            <div className={styles.breadcrumb}>
              <span>Workspace</span>
              <span aria-hidden="true">/</span>
              <strong>{connected ? label : "Connect"}</strong>
            </div>
          </div>
          <div className={styles.headerActions}>
            <ThemeToggle />
            <Link href="/#call-me" className={styles.phoneLink}>
              <ProductIcon name="phone" />
              <span>Phone receptionist</span>
            </Link>
          </div>
        </header>
        <main id={mainId} tabIndex={-1} className={styles.content}>
          <div className={styles.pageHeading}>
            <div>
              <p className={styles.eyebrow}>HVACLINE OPERATIONS</p>
              <h1>{connected ? label : "Your service workspace"}</h1>
              <p className={styles.subtitle}>
                {section === "overview" || !connected
                  ? "A clear view of your calls, bookings and next steps."
                  : "Manage your service business, one next step at a time."}
              </p>
            </div>
            {connected && !demo && (
              <button
                type="button"
                className={styles.refreshButton}
                onClick={onRefresh}
                disabled={busy}
              >
                {busy ? "Refreshing…" : "Refresh workspace"}
              </button>
            )}
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 6h16M4 12h10M4 18h16" />
    </svg>
  );
}
