# EventFlow

**Paid ticketing for organizers — where the money and the inventory have to agree.**

[Live demo](https://eventflow-gray.vercel.app) · Django 5 · DRF · PostgreSQL · Redis · Celery · Stripe · React

EventFlow lets an organizer publish an event, define ticket types, sell them, take payment,
issue a QR ticket, scan people in at the door, and watch the numbers. The interesting part is
not the CRUD. It is that two people can hit *Buy* on the last seat at the same time, and a Stripe
webhook can arrive twice.

---

## The two failures this project is built around

**Selling the same seat twice.** Decrementing `quantity_available` after a payment is a race
with your own checkout. Inventory is instead locked and decremented inside the transaction that
creates the RSVP:

```python
with transaction.atomic():
    ticket_type = self.event.tickettype_set.select_for_update().first()
    if ticket_type.quantity_available >= self.ticket_qty:
        ticket_type.quantity_available -= self.ticket_qty
        ticket_type.save(update_fields=["quantity_available"])
    else:
        raise ValueError("Not enough tickets available")
```

**Issuing the same ticket twice.** Stripe retries webhook deliveries, and users double-click.
Checkout is a Celery task that looks for the transaction it was told about and refuses to move it
out of `PENDING` more than once:

```python
transactions = Transaction.objects.filter(session_id=session_id, payment_status="PENDING")
if not transactions.exists():
    return {"status": "already_processed", "session_id": session_id}
```

The task is `autoretry_for=(Exception,)` with exponential backoff, `acks_late` and a hard time
limit, so a dying worker loses the job back to the queue instead of losing the ticket.

---

## How a paid ticket is issued

```
Stripe Checkout  ──webhook──▶  process_checkout_session  (Celery, idempotent)
                                 ├─ mark Transaction SUCCESS
                                 ├─ create RSVP  (row-locked inventory decrement)
                                 ├─ generate QR      (segno, 1:1 with the transaction)
                                 ├─ render PDF       (WeasyPrint)
                                 └─ send email
```

Each step is a task on its own queue, so a slow PDF render cannot delay a password reset.

| Queue | Carries |
|---|---|
| `default` | checkout processing, refunds, analytics refresh |
| `emails` | ticket delivery, reminders |
| `heavy` | PDF rendering, bulk ticket generation, Stripe product sync |

Workers run with `acks_late`, `reject_on_worker_lost`, a 240 s soft and 300 s hard limit.
Beat closes finished events hourly and clears expired sessions daily.

## Analytics without aggregating on every page load

`EventAnalytics` and `TicketTypeAnalytics` are denormalized counters updated by a task whenever
an RSVP or transaction changes, so the organizer dashboard reads one row instead of scanning the
RSVP table. The parts that genuinely need history — twelve months of revenue, attendees and
events — are three `TruncMonth` aggregates joined in memory, not a query per month.

`RSVP` carries five composite indexes (`event + created_at`, `attendee + created_at`,
`transaction_id`, `is_active + is_cancelled + is_attended`, `event + is_active`) because every
dashboard and every check-in screen filters on them.

## Stack

| Layer | Choice |
|---|---|
| Web | Django 5.0, Django REST Framework, SimpleJWT, django-filter |
| Data | PostgreSQL 15, Redis 7 (broker, result backend, cache) |
| Async | Celery 5.3 + beat, django-celery-results, Flower |
| Payments | Stripe Checkout, signed webhooks, refunds |
| Documents | WeasyPrint (tickets), segno (QR) |
| Frontend | React 18 + Vite + Tailwind in [`eventflow-frontend`](https://github.com/rahulbiswas24680/eventflow-frontend) |
| Ops | Docker Compose, Nginx, Gunicorn, DigitalOcean |

## Run it

```bash
cp .env.example .env          # add Stripe test keys + webhook secret
docker compose up --build     # web, db, redis, worker, beat, flower, redis-commander
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

- App: http://localhost:8000
- Flower: http://localhost:5555
- Redis Commander: http://localhost:8081

Stripe webhooks locally:

```bash
stripe listen --forward-to localhost:8000/payments/webhook/
```

## Layout

```
events/          events, ticket types, dashboard, RSVP lifecycle, PDF tickets
payments/        cart, Stripe checkout, transactions, webhook processing, refunds
qr_codes/        QR generation and storage, bound 1:1 to a transaction
analytics/       denormalized per-event and per-ticket counters, refresh tasks
communication/   email, sessions, cleanup
registration/    attendee signup
rsvp/            project settings, Celery app, cache utilities, throttles
user_profiles/   organizer and attendee profiles, role handling
support/         contact and helpdesk
```

## Status

Feature-complete for the flows above; the test suite is still the next piece of work
(`pytest` and `pytest-django` are wired up, the test modules are stubs). Known rough edges are
tracked in issues.

## License

Private project, published for review. All rights reserved.
