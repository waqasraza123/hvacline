import { callingLaunch } from "./contracts";

export function CallingLaunchDate() {
  return <time dateTime={callingLaunch.date}>{callingLaunch.label}</time>;
}
