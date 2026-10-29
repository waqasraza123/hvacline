DEVELOPMENT_ADDITIONAL_FAQS: tuple[tuple[str, str, str], ...] = (
    (
        "air-conditioning-repair",
        "Can I request air conditioning repair?",
        "I can collect an air conditioning repair request and check available "
        "appointments. Describe the issue in your own words; a technician must "
        "assess the equipment. I cannot diagnose the fault or provide repair instructions.",
    ),
    (
        "heating-repair",
        "Can I request heating repair?",
        "I can collect a heating repair request and check available appointments. "
        "Describe the issue without attempting repairs. Equipment diagnosis and "
        "repair recommendations require a qualified technician.",
    ),
    (
        "maintenance",
        "Can I book HVAC maintenance?",
        "I can collect a maintenance request and check the booking calendar. "
        "A staff member must confirm the specific work, pricing and equipment "
        "requirements; no maintenance package or contract is promised here.",
    ),
    (
        "equipment-brands",
        "Which equipment brands do you service?",
        "No equipment-brand support list has been approved for this "
        "business. Tell me the equipment type and issue, and ask staff to confirm "
        "whether your particular make and model can be serviced.",
    ),
    (
        "service-area",
        "Do you serve my ZIP code?",
        "Please provide your five-digit U.S. service ZIP code. I must check it "
        "against the configured booking service area before offering an appointment. "
        "I cannot promise service outside the returned service area.",
    ),
    (
        "booking-process",
        "How do I book an appointment?",
        "Tell me the requested service and complete service details. I will read "
        "them back for confirmation, check available appointments, and read back "
        "your selected slot. Your appointment is booked only after you agree "
        "and the booking system returns a confirmed result.",
    ),
    (
        "required-details",
        "What information do you need to book?",
        "To book, please provide your name, "
        "callback number, full U.S. service address with ZIP code, service type, "
        "equipment issue, preferred appointment date and any reported hazard. "
        "Email is optional. Do not provide payment details or passwords.",
    ),
    (
        "availability",
        "What appointment times are available?",
        "Availability must be checked for your service ZIP code and requested "
        "date using the booking calendar. I can offer only returned slots in "
        "the business timezone; I cannot invent times or promise same-day service.",
    ),
    (
        "appointment-timezone",
        "Which timezone are appointment times shown in?",
        "Appointment times use the business timezone returned by the booking "
        "calendar. I will include that timezone when reading back your selected "
        "appointment, so you can confirm the date and time.",
    ),
    (
        "temporary-holds",
        "Is a temporary appointment hold a confirmed booking?",
        "No. A temporary hold lasts five minutes and is not a confirmed booking. "
        "You must agree after the appointment readback and receive a confirmed "
        "result from the booking system. An unconfirmed hold can expire.",
    ),
    (
        "unavailable-slots",
        "What happens if there are no appointments available?",
        "We can check another date. If the calendar is unavailable or no suitable "
        "slots are returned, staff assistance is needed. A saved service request "
        "alone does not reserve an appointment or guarantee a callback.",
    ),
    (
        "rescheduling",
        "Can I reschedule an existing appointment?",
        "Existing appointment changes require staff assistance in this version. "
        "I cannot change a confirmed appointment through the browser voice flow "
        "or promise that a replacement appointment has been booked.",
    ),
    (
        "cancellation",
        "Can I cancel an existing appointment?",
        "Cancelling an existing confirmed appointment requires staff assistance "
        "in this version. Releasing a temporary hold does not cancel a confirmed "
        "appointment. I cannot promise a cancellation or any applicable fee.",
    ),
    (
        "pricing",
        "How much does HVAC service cost?",
        "No service prices have been approved for this business. "
        "A staff member must provide estimates, fees and final pricing. "
        "Booking a visit does not establish a repair price or authorize paid work.",
    ),
    (
        "diagnostic-fees",
        "Do you charge a diagnostic or call-out fee?",
        "No diagnostic or call-out fee policy has been approved here. "
        "Please ask staff to confirm applicable charges before agreeing to work. "
        "I cannot quote a fee or promise a free visit.",
    ),
    (
        "warranty",
        "Do you offer a warranty?",
        "No warranty terms have been approved for this business. "
        "Staff must confirm any equipment or workmanship warranty and its "
        "conditions. I cannot promise coverage or eligibility.",
    ),
    (
        "payments-financing",
        "What payment and financing options do you offer?",
        "Payment methods and financing terms have not been approved here. "
        "Staff must confirm any available options and conditions. "
        "Do not provide card numbers, bank details or payment credentials to this assistant.",
    ),
    (
        "technician-arrival",
        "When will the technician arrive?",
        "I can repeat a successfully confirmed appointment date, time and "
        "business timezone from the booking result. Live technician tracking "
        "and arrival estimates are not connected, so I cannot provide a live ETA "
        "or promise an arrival beyond the confirmed appointment information.",
    ),
    (
        "human-assistance",
        "Can I speak to a staff member?",
        "Staff assistance is needed for questions or changes outside this "
        "assistant's approved scope. A transfer or callback is only a request "
        "unless the relevant system confirms its outcome. I cannot promise "
        "that someone has answered, received an alert or will call by a deadline.",
    ),
    (
        "booking-receipt",
        "Where can I see my appointment?",
        "For website bookings made while signed in, open My appointments to view "
        "the bookings associated with your account. Ask staff about bookings "
        "not linked to that account. A confirmed receipt means booked; "
        "a temporary hold is waiting for confirmation. Email and SMS reminders "
        "are not connected in this version.",
    ),
    (
        "external-calendars",
        "Will my booking appear in Google Calendar or Outlook?",
        "Appointments are stored in the internal booking calendar. "
        "Google Calendar and Outlook synchronization are not connected. "
        "For website bookings made while signed in, use My appointments to view "
        "the saved booking; other bookings require staff assistance.",
    ),
    (
        "ai-disclosure",
        "Am I speaking with an AI assistant?",
        "Yes. I am Line, an AI booking assistant. You must accept the AI "
        "disclosure before starting and microphone processing before using voice. "
        "You can stop the conversation at any time.",
    ),
    (
        "repair-instructions",
        "Can you diagnose my equipment or explain how to repair it?",
        "I cannot diagnose equipment or give repair instructions. I can collect "
        "your description of the issue for a qualified technician. Report any "
        "hazard immediately; hazardous requests cannot use routine self-booking.",
    ),
    (
        "emergency-response",
        "Do you guarantee an emergency technician or urgent response?",
        "This AI booking flow does not guarantee emergency dispatch, an urgent "
        "response time or a delivered emergency alert. Reported hazards require "
        "human attention and cannot be booked as routine service through this assistant.",
    ),
    (
        "confirmation-privacy",
        "When are my service details and transcript saved?",
        "The application saves service details and confirmed transcript text "
        "only after explicit confirmation. For website voice, draft details "
        "remain in browser memory before saving. The application does not store raw audio.",
    ),
)
