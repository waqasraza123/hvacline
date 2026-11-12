import type { ReactNode } from "react";
import styles from "./dashboard.module.css";

export function DashboardTable({
  caption,
  headings,
  children,
}: {
  caption: string;
  headings: readonly string[];
  children: ReactNode;
}) {
  return (
    <div
      className={styles.tableScroll}
      role="region"
      aria-label={caption}
      tabIndex={0}
    >
      <table className={styles.table}>
        <caption className={styles.srOnly}>{caption}</caption>
        <thead>
          <tr>
            {headings.map((heading) => (
              <th key={heading} scope="col">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone = ["CONFIRMED", "BOOKED", "COMPLETED"].includes(status)
    ? "success"
    : ["FAILED", "REJECTED", "CANCELLED"].includes(status)
      ? "error"
      : ["REQUESTED", "ACKNOWLEDGED", "HELD"].includes(status)
        ? "warning"
        : "neutral";
  return (
    <span className={styles.badge} data-tone={tone}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
