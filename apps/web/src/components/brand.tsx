import Link from "next/link";
export function Brand() {
  return (
    <Link aria-label="HVACLine AI home" className="brand-link" href="/">
      <svg
        aria-hidden="true"
        width="36"
        height="36"
        viewBox="0 0 36 36"
        className="brand-symbol"
      >
        <rect
          width="36"
          height="36"
          rx="11"
          fill="var(--brand-charcoal)"
        />
        <path
          d="M9 15v6m6-11v16m6-16v16m6-11v6M15 18h6"
          fill="none"
          stroke="var(--brand-orange)"
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
