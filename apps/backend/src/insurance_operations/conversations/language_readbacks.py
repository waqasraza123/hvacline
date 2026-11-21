from insurance_operations.voice_languages import LanguageCode
from insurance_operations.hvac.schemas import ServiceKind, ServiceRequestInput

# Templates require owner/native-speaker acceptance before provider enablement.
INTAKE_TEMPLATES: dict[str, str] = {
    "es": "Confirme estos datos. Nombre: {name}. Teléfono: {phone}. Correo: {email}. Dirección: {address}. Servicio: {service}. Problema: {issue}. Horario preferido: {window}. Peligro: {hazard}. ¿Puedo guardar estos datos y la transcripción de la conversación? Responda sí para guardar la solicitud o indique qué debemos corregir.",
    "fr": "Veuillez confirmer ces informations. Nom : {name}. Téléphone : {phone}. E-mail : {email}. Adresse : {address}. Service : {service}. Problème : {issue}. Créneau souhaité : {window}. Danger : {hazard}. Puis-je enregistrer ces informations et la transcription de la conversation ? Répondez oui pour enregistrer la demande ou indiquez les corrections.",
    "ar": "يرجى تأكيد هذه التفاصيل. الاسم: {name}. الهاتف: {phone}. البريد الإلكتروني: {email}. العنوان: {address}. الخدمة: {service}. المشكلة: {issue}. الوقت المفضل: {window}. خطر: {hazard}. هل تسمح بحفظ هذه التفاصيل ونص المحادثة؟ أجب بنعم لحفظ الطلب أو وضح ما يجب تصحيحه.",
    "hi": "कृपया इन विवरणों की पुष्टि करें। नाम: {name}। फ़ोन: {phone}। ईमेल: {email}। पता: {address}। सेवा: {service}। समस्या: {issue}। पसंदीदा समय: {window}। खतरा: {hazard}। क्या मैं ये विवरण और बातचीत का प्रतिलेख सहेज सकता हूँ? अनुरोध सहेजने के लिए हाँ कहें या सुधार बताएं।",
    "zh": "请确认以下信息。姓名：{name}。电话：{phone}。电子邮箱：{email}。地址：{address}。服务：{service}。问题：{issue}。首选时间：{window}。危险情况：{hazard}。可以保存这些信息和对话文字记录吗？请回答是以保存请求，或说明需要更正的内容。",
    "ur": "براہ کرم ان تفصیلات کی تصدیق کریں۔ نام: {name}۔ فون: {phone}۔ ای میل: {email}۔ پتہ: {address}۔ سروس: {service}۔ مسئلہ: {issue}۔ پسندیدہ وقت: {window}۔ خطرہ: {hazard}۔ کیا میں یہ تفصیلات اور گفتگو کا متن محفوظ کر سکتا ہوں؟ درخواست محفوظ کرنے کے لیے ہاں کہیں یا تصحیح بتائیں۔",
}
APPOINTMENT_TEMPLATES: dict[str, str] = {
    "es": "Su cita está reservada temporalmente para {time}, zona horaria {timezone}. Todavía no está confirmada. ¿Puedo confirmar esta cita? Responda sí para confirmar o no para rechazar.",
    "fr": "Votre rendez-vous est temporairement réservé pour {time}, fuseau horaire {timezone}. Il n'est pas encore confirmé. Puis-je confirmer ce rendez-vous ? Répondez oui pour confirmer ou non pour refuser.",
    "ar": "موعدك محجوز مؤقتًا في {time}، بالمنطقة الزمنية {timezone}. لم يتم تأكيده بعد. هل يمكنني تأكيد هذا الموعد؟ أجب بنعم للتأكيد أو لا للرفض.",
    "hi": "आपकी मुलाकात {time}, समय क्षेत्र {timezone} के लिए अस्थायी रूप से रोकी गई है। अभी बुकिंग पक्की नहीं हुई है। क्या मैं इस मुलाकात की पुष्टि कर सकता हूँ? पुष्टि के लिए हाँ या मना करने के लिए नहीं कहें।",
    "zh": "已为您暂时保留 {time} 的预约，时区为 {timezone}。预约尚未确认。可以确认此预约吗？请回答是以确认，或回答否以拒绝。",
    "ur": "آپ کی ملاقات {time}، ٹائم زون {timezone} کے لیے عارضی طور پر محفوظ ہے۔ بکنگ ابھی پکی نہیں ہوئی۔ کیا میں اس ملاقات کی تصدیق کر سکتا ہوں؟ تصدیق کے لیے ہاں یا انکار کے لیے نہیں کہیں۔",
}
CONFIRMATIONS: dict[str, set[str]] = {
    "es": {"sí", "si", "confirmo", "sí confirmo"},
    "fr": {"oui", "je confirme", "oui je confirme"},
    "ar": {"نعم", "أؤكد", "نعم أؤكد"},
    "hi": {"हाँ", "हां", "हाँ पुष्टि करता हूँ", "हाँ पुष्टि करती हूँ"},
    "zh": {"是", "是的", "确认", "我确认"},
    "ur": {"ہاں", "جی ہاں", "میں تصدیق کرتا ہوں", "میں تصدیق کرتی ہوں"},
}
HAZARDS = {
    "es": ("no indicado", "indicado"), "fr": ("non signalé", "signalé"),
    "ar": ("لم يتم الإبلاغ", "تم الإبلاغ"), "hi": ("नहीं बताया गया", "बताया गया"),
    "zh": ("未报告", "已报告"), "ur": ("اطلاع نہیں دی گئی", "اطلاع دی گئی"),
}
NO_EMAIL = {"es": "no indicado", "fr": "non indiqué", "ar": "غير محدد", "hi": "नहीं दिया गया", "zh": "未提供", "ur": "فراہم نہیں کیا گیا"}
SERVICE_LABELS: dict[str, dict[ServiceKind, str]] = {
    "es": {ServiceKind.AC_REPAIR: "reparación de aire acondicionado", ServiceKind.HEATING_REPAIR: "reparación de calefacción", ServiceKind.INSTALLATION: "instalación", ServiceKind.MAINTENANCE: "mantenimiento"},
    "fr": {ServiceKind.AC_REPAIR: "réparation de climatisation", ServiceKind.HEATING_REPAIR: "réparation de chauffage", ServiceKind.INSTALLATION: "installation", ServiceKind.MAINTENANCE: "entretien"},
    "ar": {ServiceKind.AC_REPAIR: "إصلاح مكيف الهواء", ServiceKind.HEATING_REPAIR: "إصلاح التدفئة", ServiceKind.INSTALLATION: "تركيب", ServiceKind.MAINTENANCE: "صيانة"},
    "hi": {ServiceKind.AC_REPAIR: "AC की मरम्मत", ServiceKind.HEATING_REPAIR: "हीटिंग की मरम्मत", ServiceKind.INSTALLATION: "स्थापना", ServiceKind.MAINTENANCE: "रखरखाव"},
    "zh": {ServiceKind.AC_REPAIR: "空调维修", ServiceKind.HEATING_REPAIR: "供暖维修", ServiceKind.INSTALLATION: "安装", ServiceKind.MAINTENANCE: "保养"},
    "ur": {ServiceKind.AC_REPAIR: "ایئر کنڈیشنر کی مرمت", ServiceKind.HEATING_REPAIR: "ہیٹنگ کی مرمت", ServiceKind.INSTALLATION: "تنصیب", ServiceKind.MAINTENANCE: "دیکھ بھال"},
}


def localized_intake(request: ServiceRequestInput, language: LanguageCode) -> str:
    customer, service = request.customer, request.service
    address = customer.address
    if address is None:
        raise ValueError("A complete service address is required")
    street = f"{address.line1}, {address.line2}" if address.line2 else address.line1
    value = INTAKE_TEMPLATES[language].format(name=customer.full_name, phone=customer.phone,
        email=customer.email or NO_EMAIL[language],
        address=f"{street}, {address.city}, {address.state_code} {address.postal_code}, US",
        service=SERVICE_LABELS[language][service.kind], issue=service.equipment_issue, window=service.preferred_window,
        hazard=HAZARDS[language][int(service.hazardous_condition)])
    if len(value) > 1800:
        raise ValueError("Shorten the issue description before reading back the request")
    return value
