"use client";

import { useId, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import styles from "./workspace-ui.module.css";

export type SettingsTab = { key: string; label: string; content: ReactNode };

export function SettingsTabs({ tabs, label, selectedKey, onSelect }: {
  tabs: readonly SettingsTab[]; label: string;
  selectedKey?: string; onSelect?: (key: string) => void;
}) {
  const id = useId();
  const [selected, setSelected] = useState(tabs[0]?.key);
  const active = selectedKey ?? selected;
  const current = tabs.some((tab) => tab.key === active) ? active : tabs[0]?.key;
  function select(key: string) {
    if (onSelect) onSelect(key);
    else setSelected(key);
  }

  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    const tab = tabs[next];
    if (tab) {
      select(tab.key);
      event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
    }
  }

  return <div>
    <div className={styles.tabs} role="tablist" aria-label={label}>
      {tabs.map((tab, index) => <button key={tab.key} id={`${id}-${tab.key}-tab`} type="button" role="tab" className={styles.tab}
        aria-selected={current === tab.key} aria-controls={`${id}-${tab.key}-panel`} tabIndex={current === tab.key ? 0 : -1}
        onClick={() => select(tab.key)} onKeyDown={(event) => navigate(event, index)}>{tab.label}</button>)}
    </div>
    {tabs.map((tab) => <div key={tab.key} id={`${id}-${tab.key}-panel`} role="tabpanel" className={styles.tabPanel}
      aria-labelledby={`${id}-${tab.key}-tab`} hidden={current !== tab.key} tabIndex={0}>{tab.content}</div>)}
  </div>;
}
