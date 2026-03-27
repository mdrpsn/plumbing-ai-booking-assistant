# Plumbing AI Booking Assistant Backend

FastAPI backend for a plumbing-focused AI booking and customer communication workflow.

This project is structured as a public-safe portfolio backend that demonstrates lead intake, deterministic triage, booking request capture, two-way messaging, no-response follow-up automation, provider abstraction, webhook verification, idempotent processing, and migration-driven persistence.

## What This Project Demonstrates

- Production-style FastAPI service structure with clear API, service, schema, and persistence boundaries.
- Relational workflow modeling for customers, leads, conversations, messages, booking requests, audit logs, and workflow runs.
- Deterministic business logic for urgency triage and no-response follow-up behavior.
- Mock-first external integration design with a safe path for local development and public repository use.
- Configurable SMS provider support with a Twilio integration path behind a shared abstraction.
- Idempotent inbound webhook handling and duplicate-safe workflow execution.
- Alembic-based schema management instead of runtime schema mutation.
- A local-first execution boundary that can evolve into a real worker/queue architecture.

## Architecture Overview

At a high level, the system accepts customer leads, persists operational records in SQLite through SQLAlchemy, and coordinates communication and follow-up behavior through service-layer workflow logic.

```text
Client / Webhook
  -> FastAPI routes
  -> Schemas + validation
  -> Service layer
  -> SQLAlchemy models / SQLite
  -> Provider abstraction (mock or Twilio)
```

Core architectural pieces:

- `app/api/routes/`: HTTP entrypoints for health, leads, bookings, messages, and workflow processing.
- `app/services/`: domain services for triage, SMS delivery, inbound message handling, follow-up logic, webhook verification, and workflow execution.
- `app/db/`: SQLAlchemy session and models.
- `app/schemas/`: request and response validation models.
- `alembic/`: database migration configuration and revision history.

## Core Domain Model

- `Customer`: canonical customer identity with normalized phone matching.
- `Lead`: a plumbing request intake event linked to a customer.
- `BookingRequest`: a persisted booking intent linked to a lead and customer.
- `Conversation`: a two-way messaging thread linked to a customer and optionally a lead.
- `Message`: inbound or outbound communication record with provider metadata and idempotency support.
- `WorkflowRun`: persisted follow-up workflow/job tracking.
- `AuditLog`: append-only operational audit trail.

## Core Flows

### Lead Intake

`POST /api/leads`

1. Validate payload.
2. Normalize the customer phone number.
3. Find or create the customer.
4. Create the lead and assign deterministic urgency.
5. Create the initial SMS conversation.
6. Persist the lead audit log.
7. Send outbound confirmation through the configured SMS provider.
8. Register a no-response follow-up workflow.

### Booking Request

`POST /api/bookings/request`

1. Validate `lead_id`.
2. Load the lead and customer context.
3. Persist a booking request record.
4. Return mock availability.
5. Write an audit log entry.

### Outbound Confirmation

Triggered during lead creation.

1. Build the confirmation message.
2. Send through the configured provider path.
3. Persist provider metadata on the `Message`.
4. Update conversation state.
5. Write an audit log entry.

### Inbound Messaging

`POST /api/messages/inbound`

1. Validate inbound payload.
2. Detect webhook replay with a persisted idempotency key.
3. Resolve the customer by normalized phone.
4. Find or create the matching conversation.
5. Persist the inbound message.
6. Update conversation state to reflect customer reply.
7. Write an audit log entry.

Twilio form/webhook path:

- `POST /api/messages/providers/twilio/inbound`

### No-Response Follow-Up

Lead creation registers a `WorkflowRun` for delayed follow-up evaluation.

`POST /api/workflows/follow-ups/process`

1. Pull due workflow jobs from the local execution boundary.
2. Reuse the same execution service a future worker would call.
3. Skip workflows if the customer already replied.
4. Reuse an existing follow-up result if one was already created.
5. Otherwise create and send a follow-up outbound message.
6. Update workflow, conversation, and audit records.

### Provider Callbacks

Twilio status callback:

- `POST /api/messages/providers/twilio/status`

1. Verify the request signature when Twilio verification is enabled.
2. Resolve the message by provider message identifier.
3. Update persisted delivery status.
4. Write callback audit logs.

## API Summary

- `GET /health`
- `POST /api/leads`
- `POST /api/bookings/request`
- `POST /api/messages/inbound`
- `POST /api/messages/providers/twilio/inbound`
- `POST /api/messages/providers/twilio/status`
- `POST /api/workflows/follow-ups/process`

## Setup

### Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Default local behavior is safe and mock-first:

- SQLite is used as the database.
- `SMS_PROVIDER=mock` is the default.
- No real provider credentials are required.

### Test Run

```bash
python -m pytest
```

## Database Migrations

Migration commands:

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe schema change"
alembic downgrade -1
```

Current migration history includes:

- Initial schema creation
- Customer normalized phone support
- Message idempotency key support

## Provider Configuration

### Mock Provider

Recommended for local development and tests.

```env
SMS_PROVIDER=mock
```

### Twilio Provider

Enable Twilio behind the same notification abstraction:

```env
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_PHONE=...
TWILIO_WEBHOOK_VERIFICATION_ENABLED=true
TWILIO_STATUS_CALLBACK_URL=https://your-domain.example/api/messages/providers/twilio/status
```

Optional:

- `TWILIO_API_BASE_URL` for controlled environments or alternate endpoints.

Public-safety note:

- Never commit live Twilio credentials.
- Keep secrets in environment variables only.
- The repository is designed to run safely in mock mode by default.

## Webhook Verification Behavior

- In mock mode, Twilio-specific webhook routes can be exercised locally without real credentials or signature enforcement.
- In Twilio mode, webhook verification can be enabled through `TWILIO_WEBHOOK_VERIFICATION_ENABLED=true`.
- Signature verification is intended to be bypassed only for local/mock workflows.

## Phone Normalization

- Customer matching uses a canonical normalized phone value.
- Common formats such as `5551234567`, `(555) 123-4567`, and `+1 555-123-4567` resolve to the same customer.
- Inbound message resolution uses the same normalization path as lead intake.

## Idempotency and Duplicate Protection

- Inbound replay detection uses a provider-derived idempotency key.
- Replaying the same inbound provider message does not create a duplicate `Message`.
- Follow-up processing persists workflow-specific idempotency keys.
- Re-running follow-up processing does not send the same follow-up twice.

## Execution Model

Current local-first execution:

- API route triggers workflow execution directly.
- `WorkflowJobQueue` identifies due jobs from persisted workflow records.
- `WorkflowExecutionService` dispatches workflow jobs to follow-up processing logic.

How this maps to a future Redis/worker setup:

- Replace the local queue abstraction with Redis-backed job reservation.
- Run `WorkflowExecutionService` in a separate worker process.
- Keep workflow business logic in the same service layer.
- Preserve the existing API boundary while moving execution off-request.

## Sample cURL Commands

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Create Lead

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

### Receive Local Inbound Message

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

### Twilio Status Callback Example

```bash
curl -X POST http://127.0.0.1:8000/api/messages/providers/twilio/status ^
  -H "X-Twilio-Signature: <signature>" ^
  -F "MessageSid=SM123" ^
  -F "MessageStatus=delivered"
```

## Project Structure

```text
alembic/
app/
  api/routes/
  core/
  db/
  schemas/
  services/
tests/
```

## Roadmap / Future Improvements

- Add authentication and role-based operational access for dashboard/admin use.
- Add a real calendar integration boundary for technician availability and booking confirmation.
- Add outbound email support behind the same notification abstraction.
- Introduce a Redis-backed queue and a dedicated worker process.
- Add observability primitives such as structured logging, metrics, and tracing.
- Add richer lead qualification and AI-assisted triage orchestration.
- Add conversation summarization and operator handoff tooling.
- Add CI checks for migrations, linting, and contract tests.

## Public-Safe Repository Notes

- No secrets are committed to source.
- External integrations default to mock-safe behavior.
- Example values in docs are placeholders only.
