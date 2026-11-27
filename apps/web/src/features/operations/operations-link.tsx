"use client";

import type { ComponentProps } from "react";
import { operationsHref } from "./dashboard-navigation";
import type { OperationsSection, OperationsSubpage } from "./dashboard-navigation";

export function navigateOperations(section: OperationsSection, subpage?: OperationsSubpage) {
  const href = operationsHref(section, subpage);
  if (window.location.pathname !== href || window.location.search || window.location.hash) {
    window.history.pushState(null, "", href);
  }
}

export function OperationsLink({ section, subpage, onNavigate, children, ...props }:
  Omit<ComponentProps<"a">, "href" | "onClick"> & {
    section: OperationsSection;
    subpage?: OperationsSubpage;
    onNavigate?: () => void;
  }) {
  return <a {...props} href={operationsHref(section, subpage)} onClick={(event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || props.target === "_blank") return;
    event.preventDefault();
    navigateOperations(section, subpage);
    onNavigate?.();
  }}>{children}</a>;
}
