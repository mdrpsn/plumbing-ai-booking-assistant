# Local-Service Automation Backend

Reusable FastAPI backend for local-service booking, messaging, and workflow automation.

This repository is the main public showcase. It is designed as a reusable backend platform for service businesses such as plumbing, electrical, HVAC, and similar local trades. The current implementation keeps plumbing as the flagship vertical example, while the underlying architecture is intended to be adapted across niches without rewriting the core system.

## Flagship Example

Plumbing is the primary example in this repo today:

- lead intake and deterministic urgency triage
- booking request capture
- outbound confirmation messaging
- inbound customer messaging
- no-response follow-up automation
- Twilio-ready provider callback handling

## What This Project Demonstrates

- Production-style FastAPI service structure with clear route, schema, service, and persistence boundaries.
- Reusable local-service workflow modeling for customers, leads, conversations, messages, booking requests, audit logs, and workflow runs.
- Mock-first integration design that is safe for a public portfolio repository.
- Migration-driven persistence with Alembic instead of runtime schema patching.
- Configurable SMS delivery path with mock and Twilio implementations.
- Idempotent inbound messaging and duplicate-safe workflow processing.
- A worker-oriented execution boundary that can evolve into a real queue/worker deployment.

## Architecture Overview

```text
Client / Webhook
  -> FastAPI routes
  -> Pydantic schemas
  -> Service layer
  -> SQLAlchemy models
  -> SQLite
  -> Provider abstraction (mock / Twilio)
```

Primary code areas:

- `app/api/routes/`: HTTP endpoints
- `app/services/`: business logic, provider integrations, execution boundary
- `app/db/`: models and database session
- `app/schemas/`: request/response models
- `alembic/`: migration history

## Core Platform vs Vertical-Specific

### Core Platform

These parts are broadly reusable across local-service businesses:

- customer identity resolution and phone normalization
- lead, booking, message, conversation, audit, and workflow persistence
- provider abstraction for outbound SMS
- inbound webhook handling and idempotency
- workflow execution boundary and delayed follow-up processing
- Alembic migrations and environment-driven configuration

### Vertical-Specific

These parts are expected to vary by niche:

- urgency triage rules and keywords
- service types and booking categories
- customer-facing message copy
- intake fields and qualification rules
- follow-up timing or escalation policies

## Core Flows

### Lead Intake

`POST /api/leads`

1. Validate payload.
2. Normalize phone and find or create the customer.
3. Create the lead and assign deterministic urgency.
4. Create the initial conversation.
5. Send outbound confirmation.
6. Register a no-response follow-up workflow.

### Booking Request

`POST /api/bookings/request`

1. Validate `lead_id`.
2. Persist a booking request.
3. Return mock availability.
4. Write an audit log.

### Outbound Confirmation

Triggered during lead creation.

1. Build confirmation copy.
2. Send through the configured SMS provider.
3. Persist provider metadata on the message.
4. Update conversation state.

### Inbound Messaging

`POST /api/messages/inbound`

1. Validate inbound payload.
2. Detect replay through idempotency keys.
3. Resolve customer by normalized phone.
4. Persist inbound message and update conversation state.

Twilio inbound route:

- `POST /api/messages/providers/twilio/inbound`

### No-Response Follow-Up

`POST /api/workflows/follow-ups/process`

1. Pull due workflow jobs.
2. Skip if the customer already replied.
3. Reuse existing follow-up results if already processed.
4. Otherwise send a follow-up outbound message.
5. Update workflow, conversation, and audit state.

### Provider Callbacks

Twilio delivery status route:

- `POST /api/messages/providers/twilio/status`

The callback path verifies signatures when Twilio mode is enabled, updates message delivery status, and writes audit logs.

## Vertical Adaptation

This backend is intentionally structured so a second vertical can reuse most of the system while changing a smaller set of business rules and presentation details.

What stays the same:

- API and service boundaries
- database model structure
- messaging and follow-up workflow patterns
- provider abstraction
- migration and execution architecture

What changes by niche:

- triage logic
- service catalog language
- confirmation and follow-up copy
- operator workflows and qualification prompts

### Plumbing vs Electrical Example

Urgency triage examples:

- Plumbing: burst pipe, flooding, sewage backup, no water
- Electrical: burning smell, panel sparking, power outage, exposed wiring

Service types:

- Plumbing: drain cleaning, leak repair, water heater service, fixture installation
- Electrical: outlet repair, breaker/panel work, lighting installation, EV charger install

Messaging copy differences:

- Plumbing: “We received your plumbing request and classified it as emergency.”
- Electrical: “We received your electrical service request and flagged it for urgent safety review.”

For a dedicated adaptation guide, see [docs/vertical-adaptation.md](C:/Users/Mike/plumbing-ai-booking-assistant/docs/vertical-adaptation.md).

## Project Family

- Plumbing backend: this repository, positioned as the main flagship example
- Electrical adaptation example: `electrical-ai-booking-assistant` as proof that the core backend can be repurposed across service niches

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

Safe local defaults:

- SQLite database
- `SMS_PROVIDER=mock`
- no real credentials required

### Tests

```bash
python -m pytest
```

## Database Migrations

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe schema change"
alembic downgrade -1
```

## Provider Configuration

### Mock Provider

```env
SMS_PROVIDER=mock
```

### Twilio Provider

```env
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_PHONE=...
TWILIO_WEBHOOK_VERIFICATION_ENABLED=true
TWILIO_STATUS_CALLBACK_URL=https://your-domain.example/api/messages/providers/twilio/status
```

Optional:

- `TWILIO_API_BASE_URL`

Public-safe guidance:

- never commit live credentials
- keep secrets in environment variables only
- use mock mode for local demos and portfolio review

## Sample cURL Commands

### Health

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

### Receive Inbound Message

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

### Twilio Status Callback

```bash
curl -X POST http://127.0.0.1:8000/api/messages/providers/twilio/status ^
  -H "X-Twilio-Signature: <signature>" ^
  -F "MessageSid=SM123" ^
  -F "MessageStatus=delivered"
```

## Roadmap / Future Improvements

- Add configurable vertical profiles or vertical config modules.
- Add richer per-vertical triage and service catalogs.
- Add authentication and operator-facing admin workflows.
- Add Redis-backed queueing and dedicated workers.
- Add observability primitives such as metrics, tracing, and structured logs.
- Add more provider integrations beyond Twilio.

## Public-Safe Notes

- No secrets are committed to source.
- Mock-safe defaults remain in place.
- Example values are placeholders only.
