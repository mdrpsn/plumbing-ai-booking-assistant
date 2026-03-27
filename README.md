# Plumbing AI Booking Assistant Backend

Phase 4A adds a real SMS provider boundary with configuration-driven selection, while keeping mock delivery as the default safe path for local development and tests.

## Features

- `GET /health` returns a simple status payload.
- `POST /api/leads` finds or creates a customer, stores the lead in SQLite, assigns `emergency`, `standard`, or `review`, persists an outbound confirmation message, sends it through a mock SMS provider, and writes audit logs.
- `POST /api/bookings/request` validates `lead_id`, persists a booking request, returns the saved record, and writes an audit log.
- `POST /api/messages/inbound` validates an inbound SMS payload, resolves the customer, creates or reuses a conversation, persists the inbound message, updates conversation state, and writes an audit log.
- `POST /api/workflows/follow-ups/process` evaluates due follow-up workflows and sends reminder messages when a customer has not replied.
- Workflow execution is routed through a reusable execution service and lightweight job queue abstraction that can later back a real worker process.
- SMS delivery is selected from configuration, with `mock` as the default provider and `twilio` available behind the same abstraction.
- Configuration is environment-driven with no secrets committed to source.
- SQLite remains the backing store and external integrations stay mocked.
- Database schema changes are managed through Alembic migrations.
- Customer identity resolution uses canonical normalized phone values, so common phone input formats resolve to the same customer record.
- Inbound webhooks and follow-up processing are idempotent and safe to replay.

## Data Model

- `Customer`: the caller or homeowner record keyed operationally by phone and email.
- `Customer`: the caller or homeowner record keyed operationally by a canonical normalized phone value, while preserving the latest raw phone input for display and messaging.
- `Lead`: an intake event linked to a customer and triaged deterministically.
- `BookingRequest`: a persisted booking workflow record linked to both the lead and customer.
- `AuditLog`: an append-only operational log for lead intake and booking request events.
- `Conversation`: a two-way messaging thread linked to a customer and optionally to a lead.
- `Message`: a persisted communication record linked to a customer and optionally to the originating lead.
- `WorkflowRun`: a persisted job record used to track delayed no-response follow-up evaluation and outcomes.

## Messaging Flow

1. `POST /api/leads` receives intake data and creates the customer and lead records.
2. The service creates an `sms` `Conversation` for that lead.
3. The service builds an outbound confirmation SMS message for that lead.
4. The outbound message is sent through a notification abstraction backed by a mock SMS provider.
5. The service persists the `Message` record with provider metadata and delivery status.
6. The service registers a delayed no-response `WorkflowRun`.
7. The service writes an `AuditLog` entry for the notification action.

## Inbound Messaging Flow

1. `POST /api/messages/inbound` validates the inbound webhook payload.
2. The service resolves the customer by phone number.
3. The service checks the persisted inbound idempotency key derived from the provider message identifier.
4. If the webhook is a replay, the existing `Message` record is returned without creating duplicates.
5. Otherwise, the service finds or creates the matching `Conversation` for the customer and lead.
6. The service persists the inbound `Message` with direction `inbound`.
7. The service updates conversation state to reflect the customer reply.
8. The service writes an `AuditLog` entry for the inbound message event.

## Follow-Up Workflow

1. Lead creation registers a pending no-response `WorkflowRun` with a deterministic delay.
2. A workflow execution service pulls due jobs from a lightweight local job queue abstraction.
3. `POST /api/workflows/follow-ups/process` uses the same execution service that a background worker would use.
4. Due pending workflow runs are executed through the follow-up processor.
5. If an inbound customer message exists for the conversation, the workflow is marked `skipped`.
6. If a follow-up message was already created for the workflow, the workflow reuses that persisted result instead of sending again.
7. If no inbound reply exists and no prior follow-up exists, the service creates and sends an outbound follow-up `Message`.
8. The conversation state, workflow status, and audit logs are updated with the outcome.

## Execution Architecture

- `app/api/routes/workflows.py` is now a thin API adapter over the workflow execution service.
- `app/services/workflow_execution.py` provides a reusable execution boundary with a local `WorkflowJobQueue` and `WorkflowExecutionService`.
- `app/services/follow_up.py` contains the workflow-specific business logic for executing one no-response follow-up workflow run.
- In the current local-first model, the API route invokes the execution service directly against SQLite.
- In a future Redis/worker setup, the same execution service can run in a separate worker process while the queue abstraction is replaced with Redis-backed job reservation and dispatch.

## SMS Provider Selection

- `SMS_PROVIDER=mock` is the default and is used for local development and tests.
- `SMS_PROVIDER=twilio` enables the Twilio-backed implementation behind the same notification abstraction.
- Lead confirmations and follow-up messages both use the configured provider path.
- Twilio inbound and delivery callback routes can verify request signatures when Twilio mode is enabled.
- No credentials are required for tests because the default provider remains mock-based.
- Do not commit live Twilio credentials; configure them only through environment variables.

Required environment variables when `SMS_PROVIDER=twilio`:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE`
- `TWILIO_WEBHOOK_VERIFICATION_ENABLED`
- Optional: `TWILIO_API_BASE_URL` if you need a non-default API host for controlled environments.
- Optional: `TWILIO_STATUS_CALLBACK_URL` to let Twilio post delivery events back to the app.

## Provider Callback Flow

1. When `SMS_PROVIDER=twilio`, outbound SMS sends can include `TWILIO_STATUS_CALLBACK_URL`.
2. Twilio can POST delivery events to `POST /api/messages/providers/twilio/status`.
3. The app verifies the `X-Twilio-Signature` header when verification is enabled in Twilio mode.
4. Matching `Message` records are updated with the new provider delivery status.
5. The app writes `AuditLog` entries for callback processing.

Twilio inbound webhook route:

- `POST /api/messages/providers/twilio/inbound`

Local/mock safety:

- In mock mode, Twilio-specific webhook routes can be exercised locally without real credentials or signature enforcement.
- Signature verification should only be bypassed in local/mock mode.

## Request Flow

1. `POST /api/leads` receives intake data.
2. The service normalizes the phone number and finds or creates a `Customer`.
3. The service creates a linked `Lead` with deterministic urgency.
4. The service writes an `AuditLog` entry for the new lead.
5. The service creates and sends a confirmation `Message`, then writes a notification `AuditLog`.
6. Customers can reply through `POST /api/messages/inbound`, which updates the linked conversation state.
7. Follow-up processing can send a reminder message if the customer has not replied within the configured threshold.
8. `POST /api/bookings/request` validates the lead, stores a `BookingRequest`, returns mocked availability, and writes another `AuditLog` entry.

## Phone Normalization

- Customer lookups use a canonical normalized phone format.
- Inputs such as `5551234567`, `(555) 123-4567`, and `+1 555-123-4567` resolve to the same normalized value.
- Inbound messaging resolution uses the same normalized phone matching logic as lead creation.

## Idempotency

- Inbound webhook replay is detected from the provider message identifier and returns the existing persisted message instead of creating a duplicate.
- Follow-up processing persists a workflow-specific idempotency key on the outbound follow-up message.
- Re-running follow-up processing after a successful send does not create a second follow-up message for the same workflow.

## Project Structure

```text
app/
  api/routes/
  core/
  db/
  schemas/
  services/
tests/
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

`FOLLOW_UP_DELAY_MINUTES` controls when a no-response workflow becomes eligible for evaluation.

## Database Migrations

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe schema change"
alembic downgrade -1
```

The initial migration lives in `alembic/versions/20260327_01_initial_schema.py` and reflects the current application schema.

## API Examples

### Health

```bash
curl http://127.0.0.1:8000/health
```

### Create a Lead

```bash
curl -X POST http://127.0.0.1:8000/api/leads ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Jordan Smith\",\"phone\":\"5551234567\",\"email\":\"jordan@example.com\",\"issue\":\"Burst pipe flooding the kitchen\",\"address\":\"123 Main St\"}"
```

### Request Booking Availability

```bash
curl -X POST http://127.0.0.1:8000/api/bookings/request ^
  -H "Content-Type: application/json" ^
  -d "{\"lead_id\":1}"
```

Sample booking response fields now include persisted record metadata such as `id`, `customer_id`, `status`, and `created_at`.

### Receive Inbound SMS

```bash
curl -X POST http://127.0.0.1:8000/api/messages/inbound ^
  -H "Content-Type: application/json" ^
  -d "{\"from_phone\":\"5551234567\",\"body\":\"Can someone come this afternoon?\",\"provider_message_id\":\"provider-inbound-001\",\"lead_id\":1}"
```

### Process Due Follow-Ups

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/follow-ups/process ^
  -H "Content-Type: application/json" ^
  -d "{\"now_at\":\"2026-03-27T14:00:00Z\"}"
```

## Testing

```bash
pytest
```
