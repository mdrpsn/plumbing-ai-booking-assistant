# Plumbing AI Booking Assistant Backend

Phase 3A replaces runtime schema patching with Alembic migrations so persistence changes are managed through an explicit migration history.

## Features

- `GET /health` returns a simple status payload.
- `POST /api/leads` finds or creates a customer, stores the lead in SQLite, assigns `emergency`, `standard`, or `review`, persists an outbound confirmation message, sends it through a mock SMS provider, and writes audit logs.
- `POST /api/bookings/request` validates `lead_id`, persists a booking request, returns the saved record, and writes an audit log.
- `POST /api/messages/inbound` validates an inbound SMS payload, resolves the customer, creates or reuses a conversation, persists the inbound message, updates conversation state, and writes an audit log.
- `POST /api/workflows/follow-ups/process` evaluates due follow-up workflows and sends reminder messages when a customer has not replied.
- Configuration is environment-driven with no secrets committed to source.
- SQLite remains the backing store and external integrations stay mocked.
- Database schema changes are managed through Alembic migrations.

## Data Model

- `Customer`: the caller or homeowner record keyed operationally by phone and email.
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
3. The service finds or creates the matching `Conversation` for the customer and lead.
4. The service persists the inbound `Message` with direction `inbound`.
5. The service updates conversation state to reflect the customer reply.
6. The service writes an `AuditLog` entry for the inbound message event.

## Follow-Up Workflow

1. Lead creation registers a pending no-response `WorkflowRun` with a deterministic delay.
2. `POST /api/workflows/follow-ups/process` evaluates due pending workflow runs.
3. If an inbound customer message exists for the conversation, the workflow is marked `skipped`.
4. If no inbound reply exists, the service creates and sends an outbound follow-up `Message`.
5. The conversation state, workflow status, and audit logs are updated with the outcome.

## Request Flow

1. `POST /api/leads` receives intake data.
2. The service finds or creates a `Customer`.
3. The service creates a linked `Lead` with deterministic urgency.
4. The service writes an `AuditLog` entry for the new lead.
5. The service creates and sends a confirmation `Message`, then writes a notification `AuditLog`.
6. Customers can reply through `POST /api/messages/inbound`, which updates the linked conversation state.
7. Follow-up processing can send a reminder message if the customer has not replied within the configured threshold.
8. `POST /api/bookings/request` validates the lead, stores a `BookingRequest`, returns mocked availability, and writes another `AuditLog` entry.

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
