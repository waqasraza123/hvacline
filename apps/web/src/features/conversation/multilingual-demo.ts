import { LANGUAGE_NAMES, type LanguageCode } from "@insurance-operations/customer-core";

export type DemoLanguage = Exclude<LanguageCode, "ur">;
type Copy = { request: string; question: string; answer: string; acknowledgement: string; summary: string; yes: string; saved: string; held: string; booked: string };
export const DEMO_COPY: Record<DemoLanguage, Copy> = {
  en: { request: "Hi, my air conditioner isn’t cooling.", question: "I can help arrange a repair. What name should I use?", answer: "Alex Morgan. Use 14 Example Lane, Demo City. Tomorrow afternoon works.", acknowledgement: "Of course. We can continue in English. I’ve kept your details.", summary: "Please confirm: Alex Morgan, 14 Example Lane, Demo City. AC repair, not cooling. Tomorrow afternoon preferred. No hazard reported. May I save these fictional details and this demo conversation?", yes: "Yes, I confirm.", saved: "Your demo request is saved. Would 14:00 on November 25, 2026 work? The business timezone is America/New_York.", held: "Your demo appointment is held for November 25, 2026 at 14:00, America/New_York. It is not booked yet. May I confirm it?", booked: "Your demo appointment is confirmed for November 25, 2026 at 14:00, America/New_York." },
  es: { request: "Hola, mi aire acondicionado no enfría.", question: "Puedo ayudarle a programar una reparación. ¿A qué nombre?", answer: "Alex Morgan. La dirección es 14 Example Lane, Demo City. Prefiero mañana por la tarde.", acknowledgement: "Claro, podemos continuar en español. Conservo sus datos.", summary: "Confirme: Alex Morgan, 14 Example Lane, Demo City. Reparación de aire acondicionado, no enfría. Prefiere mañana por la tarde. No se ha indicado ningún peligro. ¿Puedo guardar estos datos ficticios y esta conversación de demostración?", yes: "Sí, confirmo.", saved: "Su solicitud de demostración está guardada. ¿Le viene bien el 25 de noviembre de 2026 a las 14:00, zona America/New_York?", held: "Su cita de demostración está reservada temporalmente para el 25 de noviembre de 2026 a las 14:00, America/New_York. Todavía no está confirmada. ¿Puedo confirmarla?", booked: "Su cita de demostración está confirmada para el 25 de noviembre de 2026 a las 14:00, America/New_York." },
  fr: { request: "Bonjour, ma climatisation ne refroidit plus.", question: "Je peux vous aider à organiser une réparation. À quel nom ?", answer: "Alex Morgan. L’adresse est 14 Example Lane, Demo City. Demain après-midi me convient.", acknowledgement: "Bien sûr, continuons en français. Vos informations sont conservées.", summary: "Veuillez confirmer : Alex Morgan, 14 Example Lane, Demo City. Réparation de climatisation, ne refroidit plus. Demain après-midi souhaité. Aucun danger signalé. Puis-je enregistrer ces informations fictives et cette conversation de démonstration ?", yes: "Oui, je confirme.", saved: "Votre demande de démonstration est enregistrée. Le 25 novembre 2026 à 14:00, fuseau America/New_York, vous convient-il ?", held: "Votre rendez-vous de démonstration est temporairement réservé pour le 25 novembre 2026 à 14:00, America/New_York. Il n’est pas encore confirmé. Puis-je le confirmer ?", booked: "Votre rendez-vous de démonstration est confirmé pour le 25 novembre 2026 à 14:00, America/New_York." },
  ar: { request: "مرحبًا، مكيف الهواء لا يبرد.", question: "يمكنني مساعدتك في ترتيب الإصلاح. ما الاسم؟", answer: "Alex Morgan. العنوان 14 Example Lane, Demo City. أفضل عصر الغد.", acknowledgement: "بالطبع، يمكننا المتابعة بالعربية. احتفظت بتفاصيل طلبك.", summary: "يرجى التأكيد: Alex Morgan، 14 Example Lane, Demo City. إصلاح مكيف لا يبرد. الوقت المفضل عصر الغد. لا يوجد خطر مُبلّغ عنه. هل تسمح بحفظ هذه التفاصيل الخيالية ونص هذه المحادثة التجريبية؟", yes: "نعم، أؤكد.", saved: "تم حفظ طلبك التجريبي. هل يناسبك 25 نوفمبر 2026 الساعة 14:00 بتوقيت America/New_York؟", held: "موعدك التجريبي محجوز مؤقتًا في 25 نوفمبر 2026 الساعة 14:00، America/New_York. لم يتم تأكيده بعد. هل يمكنني تأكيده؟", booked: "تم تأكيد موعدك التجريبي في 25 نوفمبر 2026 الساعة 14:00، America/New_York." },
  hi: { request: "नमस्ते, मेरा AC ठंडा नहीं कर रहा है।", question: "मैं मरम्मत का समय तय करने में मदद कर सकता हूँ। आपका नाम क्या है?", answer: "Alex Morgan। पता 14 Example Lane, Demo City है। कल दोपहर ठीक रहेगा।", acknowledgement: "ज़रूर, हम हिंदी में बात कर सकते हैं। आपके विवरण सुरक्षित हैं।", summary: "कृपया पुष्टि करें: Alex Morgan, 14 Example Lane, Demo City। AC की मरम्मत, ठंडा नहीं हो रहा। पसंदीदा समय कल दोपहर। कोई खतरा नहीं बताया गया। क्या मैं ये काल्पनिक विवरण और यह डेमो बातचीत सहेज सकता हूँ?", yes: "हाँ, मैं पुष्टि करता हूँ।", saved: "आपका डेमो अनुरोध सहेजा गया है। क्या 25 नवंबर 2026 को 14:00 बजे, America/New_York समय ठीक है?", held: "आपकी डेमो मुलाकात 25 नवंबर 2026 को 14:00 बजे, America/New_York समय पर अस्थायी रूप से रोकी गई है। बुकिंग अभी पक्की नहीं है। क्या मैं इसकी पुष्टि कर सकता हूँ?", booked: "आपकी डेमो मुलाकात 25 नवंबर 2026 को 14:00 बजे, America/New_York समय पर पक्की हो गई है।" },
  zh: { request: "你好，我的空调不制冷了。", question: "我可以帮您安排维修。请问您的姓名？", answer: "Alex Morgan。地址是 14 Example Lane, Demo City。希望明天下午上门。", acknowledgement: "当然，我们可以继续用中文交流。您的信息已保留。", summary: "请确认：Alex Morgan，14 Example Lane, Demo City。空调维修，不制冷。首选明天下午。未报告危险情况。可以保存这些虚构信息和演示对话吗？", yes: "是的，我确认。", saved: "您的演示请求已保存。2026年11月25日14:00，America/New_York 时区，方便吗？", held: "已为您暂时保留2026年11月25日14:00的演示预约，时区为 America/New_York。预约尚未确认。可以确认吗？", booked: "您的演示预约已确认：2026年11月25日14:00，America/New_York 时区。" },
};
export type DemoTurn = { speaker: "CUSTOMER" | "LINE"; text: string; language: DemoLanguage };
export type MultilingualDemo = {
  language: DemoLanguage; stage: "intake" | "readback" | "saved" | "held" | "booked";
  turns: DemoTurn[]; switches: number; interrupted: boolean;
  details: { name: string; address: string; serviceKind: "AC_REPAIR"; preferred: string; requestId: string; appointmentId: string };
};
export function initialMultilingualDemo(language: DemoLanguage = "en"): MultilingualDemo {
  const copy = DEMO_COPY[language];
  return { language, stage: "intake", switches: 0, interrupted: false,
    turns: [{ speaker: "CUSTOMER", text: copy.request, language }, { speaker: "LINE", text: copy.question, language }, { speaker: "CUSTOMER", text: copy.answer, language }],
    details: { name: "Alex Morgan", address: "14 Example Lane, Demo City", serviceKind: "AC_REPAIR", preferred: "2026-11-25 afternoon · America/New_York", requestId: "DEMO-REQUEST-104", appointmentId: "DEMO-APPOINTMENT-204" } };
}
export type DemoAction = { type: "language"; language: DemoLanguage } | { type: "advance" | "interrupt" | "reset" | "mixed" | "background" | "unsupported" | "ambiguous" };
export function multilingualDemoReducer(state: MultilingualDemo, action: DemoAction): MultilingualDemo {
  const copy = DEMO_COPY[state.language];
  const append = (speaker: DemoTurn["speaker"], text: string, language = state.language): DemoTurn => ({ speaker, text, language });
  if (action.type === "reset") return initialMultilingualDemo();
  if (state.stage === "booked") return state;
  if (action.type === "mixed" && state.stage !== "intake") return state;
  if ((action.type === "ambiguous" || action.type === "interrupt") && !["readback", "held"].includes(state.stage)) return state;
  if (action.type === "language") {
    if (state.language === action.language || state.stage === "booked") return state;
    const next = DEMO_COPY[action.language];
    const readback = state.stage === "readback" ? next.summary : state.stage === "held" ? next.held : null;
    return { ...state, language: action.language, switches: state.switches + 1, interrupted: false,
      turns: [...state.turns, append("CUSTOMER", `Can we speak ${LANGUAGE_NAMES[action.language]}?`, "en"),
        append("LINE", next.acknowledgement, action.language), ...(readback ? [append("LINE", readback, action.language)] : [])] };
  }
  if (action.type === "mixed") return { ...state, turns: [...state.turns,
    append("CUSTOMER", "AC cooling नहीं कर रहा है. Tomorrow afternoon ठीक है.", "hi"),
    append("LINE", "मैं समझ गया। आपके AC repair के विवरण वही हैं।", "hi")], language: "hi", switches: state.switches + (state.language === "hi" ? 0 : 1) };
  if (action.type === "background") return { ...state, turns: [...state.turns,
    append("LINE", "[DEMO: isolated background speech ignored. Language and customer details are unchanged.]", "en")] };
  if (action.type === "unsupported") return { ...state, turns: [...state.turns,
    append("CUSTOMER", "Can we speak a language that is not configured?", "en"),
    append("LINE", "[DEMO: that language is unavailable. Continue in a configured language or request staff assistance. No transfer has been initiated.]", "en")] };
  if (action.type === "ambiguous" || action.type === "interrupt") return { ...state, interrupted: true,
    turns: [...state.turns, append("CUSTOMER", action.type === "interrupt" ? "Wait—" : "Maybe…", "en"),
      append("LINE", "[DEMO: nothing confirmed. Repeat the complete readback and ask for a fresh explicit answer.]", "en")] };
  if (state.stage === "booked") return state;
  if (state.interrupted) return { ...state, interrupted: false, turns: [...state.turns,
    append("LINE", state.stage === "held" ? copy.held : copy.summary)] };
  if (state.stage === "intake") return { ...state, stage: "readback", turns: [...state.turns, append("LINE", copy.summary)] };
  if (state.stage === "readback") return { ...state, stage: "saved", turns: [...state.turns, append("CUSTOMER", copy.yes), append("LINE", copy.saved)] };
  if (state.stage === "saved") return { ...state, stage: "held", turns: [...state.turns, append("CUSTOMER", copy.yes), append("LINE", copy.held)] };
  return { ...state, stage: "booked", turns: [...state.turns, append("CUSTOMER", copy.yes), append("LINE", copy.booked)] };
}
