# HVACLine homepage copy

Applied to the homepage source with option 1. Implementation is owner-unverified. Trust wording uses live scheduling and explicit confirmation; no answer-rate, booking-time, uptime or revenue metrics are asserted.

## Hero options, ranked

1. **Stop losing jobs to missed calls.** Leads with the owner's revenue problem; the category line and supporting copy explain the product and booking action.
2. **An AI receptionist that books HVAC appointments.** States the category, industry and outcome immediately, with less emphasis on the owner's pain.
3. **Less phone tag. More HVAC appointments.** Connects scheduling friction to the business outcome in eight words.

## Hero — updated October 31

AI voice receptionist for HVAC

**Stop losing jobs to missed calls.**

Line answers questions, checks available times, and books HVAC appointments in one natural conversation.

Secondary link: **See how it works**

### Line card

Meet Line — Your AI voice receptionist

Voice AI / Text chat (Voice AI selected initially)

**Talk it through. Book with Line.**

Tell Line what you need. Find a time that works.

Primary CTA: **Start voice chat**

Sign in, then choose Voice to get started.

Microphone access starts only with your permission.

The public business number and dial links are hidden. Text chat retains its
one-message guest exchange and sign-in continuation. Implementation/rendering
remain **UNVERIFIED**; owner checks: [homepage hero](homepage-hero.md).

## How it works

How Line books an appointment

**Three steps. One confirmed appointment.**

Homeowners describe the problem, choose an available time, and confirm. Your team skips the scheduling callbacks.

### 01 — Line hears the problem.

The homeowner explains what's wrong. Line collects the service needed, address, and contact details in a natural conversation.

Graphic: “The AC isn't cooling.”

### 02 — Line offers available times.

Line checks the business's schedule and service area, then reads out available appointment slots. The homeowner picks a time.

Graphic: Live appointment slots. Caller chooses.

### 03 — The caller confirms. Line books.

Line reads back the appointment details and asks for explicit confirmation before saving the booking.

Graphic: Details read back. Caller confirms the booking.

## Services

- **AC repair:** Book visits for cooling problems.
- **Heating repair:** Schedule heating repair visits.
- **Installation:** Book installation consultations.
- **Maintenance:** Schedule routine HVAC service.

## FAQ

**What HVAC owners need to know.**

**Who is HVACLine for?**

HVAC businesses losing appointment opportunities to missed calls and phone tag. Line handles the booking conversation, from the homeowner's first description to a confirmed appointment.

**Can homeowners speak naturally?**

Yes. Homeowners explain the problem in their own words. Line asks for the details needed to schedule the visit and offers available appointment times during the conversation.

**Are the appointment times real?**

Yes. Line checks live availability against the business's configured schedule and service area before offering times.

**When does an appointment become a booking?**

After Line reads back the appointment details and the caller explicitly confirms. A suggested time or temporary hold is not a confirmed booking.

**Can I try the conversation?**

Yes. Open the booking demo, sign in, and choose Voice to speak with Line through your browser's microphone.

## Final CTA

Try the booking conversation

**Hear Line book an HVAC appointment.**

CTA: **Try the booking demo**

## Navigation, footer and launcher

Navigation: How it works / Services / Sign in / Try the booking demo

Footer: AI voice receptionist. HVAC appointments booked in conversation.

Footer links: Sign in / Create an account

Fixed launcher: Try Line / AI voice receptionist for HVAC

## Search and sharing metadata

Title: HVACLine | AI Voice Receptionist for HVAC Businesses

Description: Stop losing jobs to missed calls. HVACLine talks with homeowners, checks live appointment slots, and confirms HVAC bookings in one conversation.

## Owner checks — not executed

From the repository root, run:

```bash
npm run verify:web
```

Manually inspect `/` on desktop and mobile for heading wraps, card text, FAQ layout, fixed-launcher overlap and horizontal overflow. Follow both section anchors and every demo link; verify `/book` retains the existing sign-in flow and exposes the Voice choice. Check keyboard navigation, FAQ expansion, page title and sharing metadata. Deployment remains owner-managed; publish the updated frontend on Vercel after owner review. No backend deployment, migration or configuration change is required for this copy update.
