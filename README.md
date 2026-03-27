# Plumbing AI Booking Assistant Backend

Phase 1 is a FastAPI backend for capturing plumbing leads, assigning deterministic urgency, and returning mocked booking availability.

## Features

- `GET /health` returns a simple status payload.
- `POST /api/leads` stores a lead in SQLite and assigns `emergency`, `standard`, or `review`.
- `POST /api/bookings/request` validates `lead_id` and returns mocked availability.
- Configuration is environment-driven with no secrets committed to source.

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
  -d "{\"name\":\"Jordan Smith\",\"phone\":\"5551234567\",\"issue\":\"Burst pipe flooding the kitchen\"}"
```

### Request Booking Availability

```bash
curl -X POST http://127.0.0.1:8000/api/bookings/request ^
  -H "Content-Type: application/json" ^
  -d "{\"lead_id\":1}"
```

## Testing

```bash
pytest
```
