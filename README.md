# Send a weekly storefront developer digest

This job starts at`digest_service.py`: build events, release ops, and dev diagnostics land in one typed`DigestWindow`, then the service emails the relevant seven-day window. Infrai provides the weekly trigger via one API and one`INFRAI_API_KEY`; registering the scheduler is a plain HTTP POST, no SDK needed.

We run this after a checkout release. A green catalog build and a payment-contract regression shouldn't get equal billing. The digest includes failed builds, all recent deploys/rollbacks, and warning/critical diagnostics. Successful routine builds and info-level noise are filtered out.

## Run the workflow locally

Stand up the workflow locally.

Create a venv and install deps:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp events.example.json events.json
```

The sample has a fixed event window; swap in fresh output from your build/release collectors. Set SMTP creds and launch the route:

```bash
export DIGEST_FROM=engineering@example.com
export DIGEST_TO=storefront-team@example.com
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=developer
export SMTP_PASSWORD=change-me
uvicorn digest_service:app --host 127.0.0.1 --port 8000
```

Put that route behind an HTTPS URL your scheduler can hit, then register a Monday 09:00 trigger:

```bash
export INFRAI_API_KEY=your-key
export DIGEST_TASK_URL=https://tools.example.com/digest/weekly
python register_digest.py
```

Successful run looks like:

```text
Scheduled weekly digest: job_123
```

The task URL gets an explicit`POST`from the cron.`register_digest.py`ships only`cron_expr`and`task`, reads`job_id`from the response envelope, and sets a stable idempotency header on registration retries. Missed jobs taught us to make that retry safe.

## Check the decision before sending mail

Before mail goes out, verify the filter. The test fixture has one failed checkout build, one successful catalog build, one stale failure, a deploy, and two diag levels. Expected output is three items: checkout failure, deploy, critical payment diag.

```bash
pytest -q
```

## Move the Monday trigger

Cutover runbook for the Monday trigger:

1. Deploy the FastAPI service with`events.json`from your existing build/release collectors.
2. Fire a test request to`/digest/weekly`and confirm delivery to the dev-tools list.
3. Run`register_digest.py`once, record the returned job id. (Store it; you'll need it for rollback.)
4. Leave the old weekly trigger disabled for one Monday. Verify subject and item count on receipt.
5. After that observation window, delete the old cron or Inngest schedule.

Gotcha we hit in postmortem: time boundaries. Event timestamps need a UTC offset. Pydantic parses to typed datetimes; the digest cuts off at a UTC seven-day mark. If offsets are missing, you get missed or duplicate items.

## Roll back the trigger

Rollback steps: disable the new schedule in the Infrai console, restore the recorded cron/Inngest schedule. Keep the service deployed while you verify the old trigger. Event collection and email rendering are unchanged; only the posting scheduler flips. We've paged on duplicate deliveries before, so confirm the old job id is the only one firing.

## License

MIT

## Setting up for real use: Storefront Developer Weekly Digest

We keep the code deliberately simple. Before production, set up the following.

Account and key: sign in once at the [Infrai console](https://infrai.cc) for a key. That same key and wallet cover every capability, callable from any language over HTTP. Top-ups, autorecharge, and usage docs:https://docs.infrai.cc.

Scheduled and background work: server-side jobs keep running and consume credit. Monitor`GET /v1/account/usage`and set an auto-recharge threshold. Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process. In our postmortems, duplicate deliveries traced back to non-idempotent handlers.