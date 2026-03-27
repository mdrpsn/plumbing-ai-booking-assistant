# Vertical Adaptation

This backend is designed so the plumbing implementation can serve as the flagship example while the same core platform is reused for other local-service businesses.

## Recommended Adaptation Strategy

Start by treating the current plumbing implementation as the reference vertical, then change only the niche-specific parts first.

Prioritize these areas:

1. Triage rules and urgency keywords
2. Service type labels and booking categories
3. Customer-facing message copy
4. Intake prompts and qualification logic
5. Follow-up timing or escalation behavior

## What Usually Stays the Same

- Customer, lead, booking, conversation, message, audit, and workflow data model shape
- API route structure
- Provider abstraction and SMS delivery path
- Inbound webhook and callback processing
- Idempotency patterns
- Workflow execution boundary
- Alembic migration workflow

## What Usually Changes

- Vertical naming in README and examples
- `triage.py` logic and emergency classification rules
- Sample payloads and service descriptions
- Booking availability assumptions
- Confirmation and follow-up message wording

## Plumbing to Electrical Example

### Urgency Differences

- Plumbing emergency examples:
  - burst pipe
  - sewage backup
  - flooding
  - no water

- Electrical emergency examples:
  - burning smell
  - sparking panel
  - exposed live wire
  - sudden outage tied to breaker/panel risk

### Service Type Differences

- Plumbing:
  - drain cleaning
  - leak repair
  - water heater service
  - fixture install

- Electrical:
  - panel upgrade
  - outlet/switch repair
  - lighting install
  - EV charger install

### Messaging Differences

- Plumbing confirmation:
  - “We received your plumbing request and classified it as emergency.”

- Electrical confirmation:
  - “We received your electrical request and flagged it for urgent safety review.”

## Adapting to Other Local-Service Niches

The same backend pattern also fits other service businesses such as HVAC, locksmith, garage door, appliance repair, pest control, and similar dispatch-oriented operations.

For a new niche, usually adapt these layers:

- Triage:
  replace the urgency keyword set and escalation rules
- Service catalog:
  rename booking and work-order categories to match the trade
- Messaging:
  update confirmation, reminder, and callback copy to fit the vertical
- Intake:
  add or revise fields that matter operationally for that service type

The platform pieces do not need to be redesigned for each niche. In most cases, the core data model, workflow execution path, webhook handling, idempotency model, and provider abstraction stay the same.

## Good Portfolio Positioning

If you publish multiple repos:

- Keep this repo as the flagship platform showcase.
- Treat niche repos as adaptation proofs, not separate one-off products.
- Link back to this repo as the reusable base architecture.

## Future Direction

A strong next step is introducing configurable vertical profiles so triage rules, service catalogs, and messaging copy can be selected from configuration instead of being embedded directly in one vertical implementation.
