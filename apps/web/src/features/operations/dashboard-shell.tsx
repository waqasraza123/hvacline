"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useId, useState } from "react";
import type { ReactNode } from "react";
import { Brand } from "@/components/brand";
import { ProductIcon } from "@/components/product-icons";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge, PageHeader } from "@/components/ui/workspace-ui";
import { navigationGroups, sections } from "./dashboard-navigation";
import type { OperationsSection } from "./dashboard-navigation";
import styles from "./dashboard.module.css";

export type { OperationsSection } from "./dashboard-navigation";

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
        {navigationGroups.map((group) => (
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
                      {item.key === "integrations" && (
                        <span
                          className={styles.navFeatureBadge}
                          aria-hidden="true"
                        >
                          CRM
                        </span>
                      )}
                      {item.key === "recovery" && <span className={styles.navFeatureBadge} aria-hidden="true">AI</span>}
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
      className={`workspace-theme ${styles.theme} ${styles.shell} ${collapsed ? styles.collapsed : ""}`}
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
            <strong>{demo ? "Demo workspace" : connected ? "Connected workspace" : "Workspace setup"}</strong>
            <p>{demo ? "Fictional sample data" : "Protected administrator access"}</p>
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
                <Dialog.Content className={`workspace-theme ${styles.theme} ${styles.drawer}`}>
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
            <span className={styles.headerStatus}><Badge tone={demo ? "accent" : "neutral"}>{demo ? "Demo data" : connected ? "Connected" : "Setup required"}</Badge></span>
            <ThemeToggle />
            <Link href="/workspace" className={styles.phoneLink} aria-label="Open staff workspace">
              <ProductIcon name="shield" />
              <span>Staff sign in</span>
            </Link>
          </div>
        </header>
        <main id={mainId} tabIndex={-1} className={styles.content}>
          <PageHeader
            title={connected ? label ?? "Workspace" : "Connect your workspace"}
            description={section === "recovery" && connected
              ? "Turn missed opportunities into the next confirmed appointment."
              : section === "integrations" && connected
                ? "Manage CRM connections, calendar booking and contact summaries."
                : section === "overview" || !connected
                  ? "Your calls, service requests and next steps, in one place."
                  : section === "multilingual"
                    ? "Explore a fictional multilingual conversation. Live languages require verified provider setup."
                    : "Manage your service business with clear, connected tools."}
            actions={connected && !demo ? <button type="button" className={styles.refreshButton}
              onClick={onRefresh} disabled={busy}>{busy ? "Refreshing…" : "Refresh workspace"}</button> : undefined}
          />
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
