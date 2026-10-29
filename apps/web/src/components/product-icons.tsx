import type { CSSProperties } from "react";

type IconName =
  | "arrow"
  | "check"
  | "snow"
  | "heat"
  | "home"
  | "shield"
  | "clock"
  | "mic"
  | "phone"
  | "chat"
  | "close"
  | "calendar"
  | "logout";

const paths: Record<IconName, string> = {
  arrow: "M5 12h14m-6-6 6 6-6 6",
  check: "m5 12 4 4L19 6",
  snow: "M12 2v20M3.34 7l17.32 10M3.34 17 20.66 7M8 4l4 3 4-3M8 20l4-3 4 3M3 11l4-2-1-5M21 13l-4 2 1 5M3 13l4 2-1 5M21 11l-4-2 1-5",
  heat: "M13 3c1 5-3 5-1 9 2-1 3-3 3-5 4 3 5 6 4 9a7 7 0 0 1-14-1c0-3 2-6 5-8-1 3 0 4 1 5 1-4 2-6 2-9Z",
  home: "m3 10 9-7 9 7M5 9v12h14V9M9 21v-8h6v8",
  shield: "m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6l8-3Zm-4 9 3 3 5-6",
  clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
  mic: "M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5ZM5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8",
  phone:
    "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.1 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 10a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2Z",
  chat: "M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Zm2 5h10m-10 4h7",
  close: "m6 6 12 12M6 18 18 6",
  calendar:
    "M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm3 10h2m4 0h2m-8 4h2",
  logout: "M9 4H4v16h5m5-12 4 4-4 4m-6-4h12",
};

export function ProductIcon({
  name,
  className,
}: {
  name: IconName;
  className?: string;
}) {
  return (
    <svg
      className={className}
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}

export function VoiceSymbol({
  active = false,
  className = "",
}: {
  active?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`voice-symbol ${active ? "is-active" : ""} ${className}`}
      aria-hidden="true"
    >
      {[17, 30, 43, 26, 37].map((height, index) => (
        <i
          key={index}
          style={
            {
              "--bar-height": `${height}px`,
              "--bar-delay": `${index * 110}ms`,
            } as CSSProperties
          }
        />
      ))}
    </span>
  );
}
