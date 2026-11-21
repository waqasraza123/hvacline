import { expect, it } from "vitest";
import { initialMultilingualDemo, multilingualDemoReducer } from "./multilingual-demo";

it("preserves details, the request and booking references across English/Spanish/back", () => {
  const initial = initialMultilingualDemo();
  const spanish = multilingualDemoReducer(initial, { type: "language", language: "es" });
  const english = multilingualDemoReducer(spanish, { type: "language", language: "en" });
  expect(english.details).toBe(initial.details);
  expect(english.switches).toBe(2);
  expect(english.stage).toBe("intake");
});
it("does not book on an interrupted or ambiguous reply", () => {
  let state = initialMultilingualDemo("es");
  for (let step = 0; step < 3; step++) state = multilingualDemoReducer(state, { type: "advance" });
  expect(state.stage).toBe("held");
  state = multilingualDemoReducer(state, { type: "interrupt" });
  state = multilingualDemoReducer(state, { type: "advance" });
  expect(state.stage).toBe("held");
  state = multilingualDemoReducer(state, { type: "ambiguous" });
  state = multilingualDemoReducer(state, { type: "advance" });
  expect(state.stage).toBe("held");
  expect(multilingualDemoReducer(state, { type: "advance" }).stage).toBe("booked");
});
it("repeats the booking readback after a language change and leaves background/unsupported speech inert", () => {
  let state = initialMultilingualDemo();
  for (let step = 0; step < 3; step++) state = multilingualDemoReducer(state, { type: "advance" });
  const spanish = multilingualDemoReducer(state, { type: "language", language: "es" });
  expect(spanish.stage).toBe("held");
  expect(spanish.turns.at(-1)?.language).toBe("es");
  expect(multilingualDemoReducer(spanish, { type: "background" }).language).toBe("es");
  expect(multilingualDemoReducer(spanish, { type: "unsupported" }).details).toBe(state.details);
  expect(multilingualDemoReducer(spanish, { type: "reset" })).toEqual(initialMultilingualDemo());
});
