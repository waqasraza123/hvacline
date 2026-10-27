import Link from "next/link";
export function Brand() {
  return (
    <Link aria-label="HVACLine AI home" className="brand-link" href="/">
      <svg aria-hidden="true" width="36" height="36" viewBox="0 0 36 36">
        <rect
          width="36"
          height="36"
          rx="11"
          fill="var(--customer-accent, #2455F5)"
        />
        <path
          d="M10 15v6m5-11v16m6-13v10m5-7v4"
          fill="none"
          stroke="var(--customer-on-accent, white)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span>
        HVAC<span className="brand-line">Line</span>
        <em>AI</em>
      </span>
    </Link>
  );
}
