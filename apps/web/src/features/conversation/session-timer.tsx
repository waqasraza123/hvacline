import styles from "./session-timer.module.css";

export function remainingSessionSeconds(deadline: number, now: number): number {
  return Math.max(0, Math.ceil((deadline - now) / 1000));
}

export function SessionTimer({
  remaining,
  maximum,
  active,
}: {
  remaining: number;
  maximum: number;
  active: boolean;
}) {
  const seconds = Math.min(maximum, Math.max(0, remaining));
  return (
    <div className={styles.timer} data-urgent={active && seconds <= 60}>
      <div>
        <span>Conversation time remaining</span>
        <strong
          role="timer"
          aria-live="off"
          aria-label={`${Math.floor(seconds / 60)} minutes ${seconds % 60} seconds remaining`}
        >
          {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
        </strong>
      </div>
      <progress
        value={seconds}
        max={maximum}
        aria-label="Conversation time remaining"
      />
    </div>
  );
}
