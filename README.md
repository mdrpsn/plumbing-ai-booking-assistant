# Plumbing AI Booking Assistant Backend

Phase 2A strengthens the FastAPI backend with customer tracking, persisted booking requests, and audit logging around core service operations.

## Features

- `GET /health` returns a simple status payload.
- `POST /api/leads` finds or creates a customer, stores the lead in SQLite, assigns `emergency`, `standard`, or `review`, and writes an audit log.
- `POST /api/bookings/request` validates `lead_id`, persists a booking request, returns the saved record, and writes an audit log.
- Configuration is environment-driven with no secrets committed to source.
- SQLite remains the backing store and external integrations stay mocked.

## Data Model

- `Customer`: the caller or homeowner record keyed operationally by phone and email.
- `Lead`: an intake event linked to a customer and triaged deterministically.
- `BookingRequest`: a persisted booking workflow record linked to both the lead and customer.
- `AuditLog`: an append-only operational log for lead intake and booking request events.

## Request Flow

1. `POST /api/leads` receives intake data.
2. The service finds or creates a `Customer`.
3. The service creates a linked `Lead` with deterministic urgency.
4. The service writes an `AuditLog` entry for the new lead.
5. `POST /api/bookings/request` validates the lead, stores a `BookingRequest`, returns mocked availability, and writes another `AuditLog` entry.

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
uvicorn app.main:app --reload
```

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

## Testing

```bash
pytest
```
