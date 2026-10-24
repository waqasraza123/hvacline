import Link from "next/link";
export function Brand() {
  return (
    <Link aria-label="HVACLine AI home" className="brand-link" href="/">
      <svg aria-hidden="true" width="32" height="32" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="9" fill="#183832" />
        <path
          d="M8 17h5l3-9 3 16 3-9h3"
          fill="none"
          stroke="#d8fa75"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span>
        HVACLine <em>AI</em>
      </span>
    </Link>
  );
}
