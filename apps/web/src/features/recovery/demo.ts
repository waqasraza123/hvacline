export type DemoStatus = "SCHEDULED" | "AWAITING_RESPONSE" | "RECOVERED" | "NEEDS_REVIEW" | "CLOSED";
export type DemoSlot = { id: string; label: string };
export type DemoCase = {
  id: string;
  customer: string;
  source: string;
  reference: string;
  service: string;
  channel: "SMS" | "VOICE";
  status: DemoStatus;
  reason: string;
  lastActivity: string;
  step: "IDLE" | "ASKED" | "SLOTS" | "BOOKED" | "DECLINED";
  appointment: DemoSlot | null;
};
export type DemoActivity = { id: string; caseId: string; message: string; channel: "SMS" | "VOICE"; time: string };
export type DemoState = { cases: DemoCase[]; selectedId: string; jobValue: number; activity: DemoActivity[]; notice: string };
export type DemoAction =
  | { type: "SELECT"; id: string }
  | { type: "START" | "YES" | "STOP" | "RESET" }
  | { type: "BOOK"; slotId: string }
  | { type: "VALUE"; value: number };

const names = ["Alex Morgan", "Jordan Ellis", "Casey Brooks", "Taylor Lane", "Riley Stone", "Jamie Reed", "Avery Blake", "Quinn Parker", "Morgan Vale", "Sam Winters", "Drew Carter", "Skyler James", "Robin Hayes", "Cameron West", "Finley Ross", "Harper Cole", "Emery Quinn", "Dakota Wells", "Reese Flynn", "Rowan Gray", "Sage Bennett", "Peyton Cross", "Elliot Hart", "Charlie Lake"];
const services = ["AC not cooling · routine repair", "Furnace tune-up · maintenance", "Heat pump inspection · routine repair", "Seasonal system maintenance"];
export const demoSlots: DemoSlot[] = [
  { id: "demo-slot-1", label: "Tue, Nov 24 · 9:00–10:00 AM ET" },
  { id: "demo-slot-2", label: "Tue, Nov 24 · 11:00 AM–12:00 PM ET" },
  { id: "demo-slot-3", label: "Tue, Nov 24 · 2:00–3:00 PM ET" },
];

export function initialDemo(): DemoState {
  const cases = names.map((customer, i): DemoCase => {
    const hour = 9 + (i % 8);
    const status: DemoStatus = i < 8 ? "RECOVERED" : i < 14 ? "SCHEDULED" : i < 19 ? "AWAITING_RESPONSE" : i < 22 ? "NEEDS_REVIEW" : "CLOSED";
    return { id: `demo-recovery-${i + 1}`, customer, source: ["Missed call", "Unfinished conversation", "Unconfirmed booking"][i % 3], reference: `DEMO-${["CALL", "CHAT", "REQUEST"][i % 3]}-${String(i + 1).padStart(3, "0")}`,
      service: services[i % services.length], channel: i % 2 ? "SMS" : "VOICE", status,
      reason: status === "NEEDS_REVIEW" ? "Fictional contact permission needs staff review. Automation is blocked." : status === "CLOSED" ? "Fictional customer declined further contact." : "Confirmed routine service details, no confirmed appointment, qualifying event ended more than 30 minutes ago. Fictional channel-specific permission is present.",
      lastActivity: `Nov 20, ${hour > 12 ? hour - 12 : hour}:${i % 2 ? "30" : "00"} ${hour < 12 ? "AM" : "PM"} ET`, step: status === "RECOVERED" ? "BOOKED" : "IDLE",
      appointment: status === "RECOVERED" ? { id: `demo-existing-${i}`, label: `Mon, Nov 23 · ${9 + (i % 3)}:00 AM ET · Demo team ${1 + (i % 2)}` } : null };
  });
  return { cases, selectedId: "demo-recovery-13", jobValue: 650, notice: "", activity: [
    { id: "demo-event-1", caseId: cases[7].id, message: "Simulated customer selection confirmed a fictional maintenance visit.", channel: "SMS", time: "Nov 20 · 11:40 AM ET" },
    { id: "demo-event-2", caseId: cases[14].id, message: "Simulated AI follow-up is awaiting a fictional customer response.", channel: "VOICE", time: "Nov 20 · 11:20 AM ET" },
    { id: "demo-event-3", caseId: cases[12].id, message: "Fictional missed call scheduled for a simulated follow-up.", channel: "VOICE", time: "Nov 20 · 11:00 AM ET" },
  ] };
}

export function availableDemoSlots(state: DemoState): DemoSlot[] {
  const occupied = new Set(state.cases.map((row) => row.appointment?.id));
  return demoSlots.filter((slot) => !occupied.has(slot.id));
}

export function demoMetrics(state: DemoState) {
  const recovered = state.cases.filter((row) => row.status === "RECOVERED").length;
  return { total: state.cases.length, recovered, scheduled: state.cases.filter((row) => row.status === "SCHEDULED").length,
    awaiting: state.cases.filter((row) => row.status === "AWAITING_RESPONSE").length, conversion: recovered / state.cases.length,
    revenue: recovered * state.jobValue };
}

export function demoReducer(state: DemoState, action: DemoAction): DemoState {
  if (action.type === "RESET") return initialDemo();
  if (action.type === "SELECT") return state.cases.some((row) => row.id === action.id) ? { ...state, selectedId: action.id, notice: "" } : state;
  if (action.type === "VALUE") return Number.isFinite(action.value) && action.value >= 0 && action.value <= 100000 ? { ...state, jobValue: action.value } : state;
  const selected = state.cases.find((row) => row.id === state.selectedId);
  if (!selected || ["RECOVERED", "CLOSED", "NEEDS_REVIEW"].includes(selected.status)) return state;
  let next = { ...selected };
  let message: string;
  if (action.type === "START" && selected.step === "IDLE") {
    next = { ...next, step: "ASKED", status: "AWAITING_RESPONSE" };
    message = `Simulated ${next.channel === "VOICE" ? "AI call introduction" : "SMS follow-up"}; no provider contacted.`;
  } else if (action.type === "YES" && selected.step === "ASKED") {
    next.step = "SLOTS";
    message = "Simulated customer replied YES. Fictional appointment slots shown.";
  } else if (action.type === "STOP" && ["ASKED", "SLOTS"].includes(selected.step)) {
    next = { ...next, step: "DECLINED", status: "CLOSED", reason: "Simulated STOP: future fictional follow-ups suppressed." };
    message = "Simulated STOP recorded. Demo case closed without booking.";
  } else if (action.type === "BOOK" && selected.step === "SLOTS") {
    const slot = availableDemoSlots(state).find((item) => item.id === action.slotId);
    if (!slot) return { ...state, notice: "This fictional slot was already selected. Choose another." };
    next = { ...next, step: "BOOKED", status: "RECOVERED", appointment: slot };
    message = "Simulated booking confirmed. Demo metrics updated; no real appointment created.";
  } else return state;
  return { ...state, cases: state.cases.map((row) => row.id === next.id ? next : row), notice: message,
    activity: [{ id: `demo-event-${state.activity.length + 1}`, caseId: next.id, message, channel: next.channel, time: "Demo session · just now" }, ...state.activity] };
}
