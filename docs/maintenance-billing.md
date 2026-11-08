# Homeowner maintenance packages and extra-hours checkout

Implementation is local and **unverified**. No tests, builds, linters, type checks,
migrations, services, Stripe setup commands, payments or deployments have run.

The owner requests homeowner packages with fixed technician maintenance hours,
payment collected immediately for the initial package, and a new checkout for
each purchase of additional hours on the existing account. Every website checkout
must remain in Stripe sandbox/test mode. This is technician labor, not AI talk time.

The gateway, checkout reservations, customer bindings, signed receipts and current
subscription reconciliation adapt the owner's local DwellCall billing module.
HVACLine retains its existing FastAPI, Neon, customer-session/MFA and Next.js
architecture. No source-project credentials or configuration values were copied.

## Package model

The shared, editable catalog lives in
`apps/backend/src/insurance_operations/billing/plans.json`. Python packages this
resource and the frontend imports the same file for its disabled draft preview.
The backend catalog is authoritative once loaded.

These amounts are **drafts**, not owner-approved service rates:

| Package   | Maintenance labor each month | Initial/monthly payment | Additional hour |
| --------- | ---------------------------- | ----------------------- | --------------- |
| Essential | 3 hours                      | $249                    | $85             |
| Comfort   | 5 hours                      | $379                    | $75             |
| Complete  | 10 hours                     | $699                    | $65             |

Amounts in the catalog are integer USD cents. Edit them before creating matching
Stripe sandbox prices. These are demonstration rates; sandbox checkout can use
them without a separate approval flag.

The initial checkout is a monthly subscription, charged immediately without a
trial. Included hours become available only for a paid current subscription
period. The monthly allowance resets after a paid renewal; unused package hours
do not roll over. The UI discloses renewal and requires confirmation before
checkout. This continues the requested subscription model; change the catalog and
recurring implementation deliberately if a different renewal period is desired.

An add-hours purchase is a separate **one-time** Checkout Session attached to the
same customer and existing package reference. Customers choose 1–40 whole hours,
see `hours × package extra-hour rate`, accept that total, and pay separately.
It does not modify the subscription, automatically bill for work, or create a
second subscription. The backend computes the amount and rejects stale totals.
The purchase snapshots the package, subscription and rate. Extra hours credit
only after a retrieved sandbox Checkout Session reports complete and paid with
the expected customer, metadata, currency and amount. The same request and
repeated webhook deliveries cannot credit hours twice.

Purchased hours remain until used, including after monthly expiry/cancellation.
New extra-hours purchases require an active paid package, while already reserved
checkouts can be resumed. Pending checkouts must be completed or explicitly
expired before changing the requested extra hours. Completed/expired requests
require a deliberate new purchase. Refunds/disputes pause purchases and labor
debits for business review; the implementation does not automatically claw back
already consumed labor or clear the review hold.

The hours cover maintenance labor only. Parts, materials, installations and other
work need a separate agreement. Payment does not book a visit, guarantee
availability, change service areas or bypass existing booking/consent gates.

## Customer and staff experience

- `/pricing` and the homepage package section show 3/5/10-hour cards, extra-hour
  rates, sandbox/draft labels and an interactive separate-payment calculator.
- `/billing` requires the existing signed-in/current-factor MFA identity. Login,
  signup and MFA preserve the billing destination. It shows the package, monthly
  hours used/left, purchased hours used/left, add-hours checkout and histories.
- The portal supports payment methods, invoice history and cancellation at period
  end. Mid-period tier switching is disabled to prevent resetting the included
  allowance through Stripe price changes. After cancellation finishes, customers
  can choose a new package; purchased-hour balances remain.
- All new asynchronous states use the same circular `LoadingSpinner`, with a
  descriptive status, disabled actions and stable surrounding layout. Sign-in,
  MFA and Operations connection use the same spinner. Reduced-motion preferences
  slow the spinner and remove decorative transitions.
- Operations → **maintenance hours** records completed labor in actual minutes
  for a confirmed, started visit linked to the homeowner's account. It spends
  current package minutes first, then purchased minutes, under the account lock.
  Insufficient credit rejects the entire debit. Booking duration alone is never
  used as actual labor. One immutable entry per appointment prevents duplicate
  consumption; a changed replay needs business review. Record work promptly in
  the intended current billing period. Phone-only visits without a verified
  homeowner-account link cannot consume another account's hours.

## Backend setup owned by the operator

Add these variables to the API environment, with secret values kept in the
provider's secret store. Existing customer portal, MFA and database settings still
apply. Billing uses the existing authenticated customer or administrator's
business context and one configured Stripe sandbox account, not Stripe Connect.

```dotenv
BILLING_ENABLED=false
STRIPE_LIVE_MODE=false
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRODUCT_ID=
STRIPE_ESSENTIAL_PRICE_ID=
STRIPE_COMFORT_PRICE_ID=
STRIPE_COMPLETE_PRICE_ID=
STRIPE_PORTAL_CONFIGURATION_ID=
```

The business is resolved automatically from the signed-in customer's stored
account; administrator labor entries use the authenticated administrator's
business. Client requests cannot select another business or customer account.
Billing rows retain their account/business foreign keys, and webhook processing
uses the saved Stripe customer binding. `BILLING_MERCHANT_AGENCY_ID` is no longer
used and can be removed from existing environments after deploying this change.
No new migration is required for automatic business resolution; the original
billing migration 0020 is still required. The web server needs its existing
`NEXT_PUBLIC_API_BASE_URL` and server-only `CUSTOMER_PORTAL_SECRET`; no Stripe
secret or publishable key is exposed to the browser. Set the API `WEB_ORIGIN` to
the intended website origin for Checkout and portal return URLs.

Install the Python dependency and apply migration 0020 before serving the new
backend. These commands are supplied for the owner and were **not executed**:

```sh
python -m pip install -e '.[dev]'
APP_ENVIRONMENT=development python -m alembic upgrade head
```

For the owner's selected **sandbox**, configure `STRIPE_SECRET_KEY=sk_test_…`
privately, review/edit the catalog, then optionally create its product, three
monthly prices and portal configuration with:

```sh
APP_ENVIRONMENT=development python -m insurance_operations.billing.cli setup-catalog
```

This setup command writes Stripe sandbox catalog objects. It prints only product,
price and portal configuration IDs for environment configuration. It does not
create a webhook, send a payment, enable billing or print credentials. Repeating
setup reuses price lookup keys for the catalog fingerprint; review existing IDs
before retries after Stripe's idempotency window. Alternatively create equivalent
USD monthly fixed prices and the described portal in Stripe Dashboard.

Create a **snapshot** webhook endpoint in that same sandbox:

```text
https://<backend-host>/api/v1/billing/webhook
```

Use API version `2026-10-28.endive`, matching the pinned Stripe SDK gateway. Store
its signing secret as `STRIPE_WEBHOOK_SECRET`. Subscribe to:

```text
checkout.session.completed
checkout.session.expired
checkout.session.async_payment_succeeded
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
customer.subscription.paused
customer.subscription.resumed
invoice.paid
invoice.payment_failed
invoice.payment_action_required
charge.refunded
charge.dispute.created
```

The endpoint bounds and verifies the original raw body, rejects live events,
persists a deduplicated receipt and retrieves current Stripe state. An old
subscription-event snapshot cannot overwrite a newer subscription. Recoverable
upstream failure returns an error so Stripe can retry; the customer can also
refresh explicitly. No separate worker is needed for this slice.

Once all identifiers and the signing secret are configured, set
`BILLING_ENABLED=true`, and deploy the updated
backend and frontend. `STRIPE_LIVE_MODE=true`, live keys and live webhook events
are rejected. A database constraint also prohibits live billing-account rows.
Existing development/privacy/customer identity restrictions remain in force.

## Unknown-result recovery

Customer creation, initial checkout and extra-hours checkout reserve durable
request identities before their respective provider writes. Retries use the same
Stripe idempotency keys. After 23 hours an unbound write is held for reconciliation
rather than issued again beyond Stripe's minimum idempotency retention window.
Do not delete reservations or fabricate a replacement customer/checkout.

After locating the exact sandbox object with matching metadata in Stripe, owner
recovery commands are:

```sh
APP_ENVIRONMENT=development python -m insurance_operations.billing.cli bind-customer ACCOUNT_UUID cus_SANDBOX_ID
APP_ENVIRONMENT=development python -m insurance_operations.billing.cli bind-checkout REQUEST_UUID cs_test_SANDBOX_ID
APP_ENVIRONMENT=development python -m insurance_operations.billing.cli bind-topup REQUEST_UUID cs_test_SANDBOX_ID
APP_ENVIRONMENT=development python -m insurance_operations.billing.cli refresh ACCOUNT_UUID
```

Each binding validates remote identity and mode; top-up binding also validates
the exact saved amount. Refund/dispute review and correction of consumed labor
remain operator reconciliation tasks; do not mutate historical ledger entries
merely to clear a UI warning. Downgrade refuses when any billing evidence exists.

## Owner verification commands — unexecuted

Run these from the repository root only when you choose to verify:

```sh
APP_ENVIRONMENT=test python -m pytest tests/test_billing.py
npm run test:web -- src/features/billing/contracts.test.ts src/features/customer/auth-continuation.test.ts
npm run verify:web
python -m ruff check apps/backend/src/insurance_operations/billing apps/backend/src/insurance_operations/database/models/billing.py tests/test_billing.py tests/database/test_billing.py migrations/versions/20261108_0020_billing.py
python -m ruff format --check apps/backend/src/insurance_operations/billing apps/backend/src/insurance_operations/database/models/billing.py tests/test_billing.py tests/database/test_billing.py migrations/versions/20261108_0020_billing.py
python -m mypy apps/backend/src/insurance_operations
```

Only use an isolated disposable `TEST_DATABASE_URL` for the following command;
the existing fixture rebuilds the schema. Keep it isolated from runtime/direct
database targets and retain shared billing evidence:

```sh
APP_ENVIRONMENT=test python -m pytest tests/database/test_billing.py tests/database/test_migrations.py tests/database/test_table_ownership.py
```

Manual acceptance, still pending:

1. Desktop and 320px/mobile: package cards, calculator, account balances, history
   overflow, keyboard/focus, reduced motion, spinner/status text and pending-action
   disabling. Refresh/page navigation must not flash invented balances.
2. With `BILLING_MERCHANT_AGENCY_ID` unset, enable billing with the sandbox
   settings above. Confirm startup and `/api/v1/billing/plans` reports
   `checkout_enabled=true`. Anonymous `/billing` → sign-in/signup → MFA →
   `/billing`. Confirm billing resolves the account's existing business. Another
   account or business must not see, cancel or spend the first homeowner's hours;
   administrator labor entries must reject another business's appointment.
3. Buy a package with Stripe test card `4242 4242 4242 4242`, a future expiry and
   any three-digit CVC. Confirm its initial price is collected immediately;
   cancel, decline and an unpaid subscription must not grant package hours.
4. Add two extra hours: verify the separate checkout price, same customer,
   unchanged subscription and exactly two credited hours after payment. Repeat
   the webhook, refresh and browser back/retry: no duplicate hours or charge.
5. Cancel an open add-hours checkout and deliberately start a different quantity.
   Cancel an unpaid initial package checkout before choosing a different package;
   this must not cancel an already paid subscription.
   Simulate a lost response and keep/retry the saved request; unresolved writes
   must never create a replacement purchase with a fresh provider key.
6. Record actual completed labor through Operations. Verify minutes, package-first
   allocation, purchased balance, duplicate replay, two concurrent debits and
   insufficient balance behavior. A scheduled appointment must not itself spend
   credit. Another business/customer's appointment must be rejected.
7. Verify the Stripe portal, cancellation at period end, failed renewal, paid
   renewal/reset, retained purchased hours and refund/dispute review hold.
8. Set a live key or `STRIPE_LIVE_MODE=true` in an isolated configuration and
   confirm rejection. A correctly signed live webhook must also be rejected.

Primary references: [Stripe sandbox testing](https://docs.stripe.com/testing),
[Checkout Sessions](https://docs.stripe.com/api/checkout/sessions/create),
[webhook signatures and delivery](https://docs.stripe.com/webhooks), and
[customer portal configuration](https://docs.stripe.com/customer-management/configure-portal).
