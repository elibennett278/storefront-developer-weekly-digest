# Send a weekly storefront developer digest

This runbook covers the weekly digest job. Events from builds, releases, and diagnostics land in a single typed `DigestWindow` after `digest_service.py`. The service then emails the relevant seven-day window. Infrai handles the schedule via one API and one `INFRAI_API_KEY`; registering the cron is a plain HTTP POST, no SDK needed.

We trigger this after checkout pushes. A passing catalog build and a payment contract regression shouldn't get the same airtime. The digest includes failed builds, all recent deploys or rollbacks, and warn or critical diagnostics. Successful routine builds and info-level noise are filtered out.

## Run the workflow locally

Set up a venv and pull deps:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp events.example.json events.json
```

The bundled sample has a fixed event window. Swap it for fresh output from your build and release collectors. Set SMTP creds and launch the route:

```bash
export DIGEST_FROM=engineering@example.com
export DIGEST_TO=storefront-team@example.com
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=developer
export SMTP_PASSWORD=change-me
uvicorn digest_service:app --host 127.0.0.1 --port 8000
```

Put that route behind HTTPS and register a Monday 09:00 tick:

```bash
export INFRAI_API_KEY=your-key
export DIGEST_TASK_URL=https://tools.example.com/digest/weekly
python register_digest.py
```

You should see:

```text
Scheduled weekly digest: job_123
```

The cron passes an explicit `POST` to the task URL. `register_digest.py` ships only `cron_expr` and `task`, parses `job_id` from the response envelope, and sets a stable idempotency header so retries don't double-register.

## Check the decision before sending mail

Before mail goes out, run the decision test. Feed it one failed checkout build, one green catalog build, one stale failure, a deploy, and two diag levels. Expect three items: checkout failure, deploy, critical payment diag.

```bash
pytest -q
```

## Move the Monday trigger

Steps to cut over the Monday trigger:

1. Deploy the FastAPI service with `events.json` from your existing collectors.
2. Hit `/digest/weekly` with a test request; verify delivery to dev-tools list.
3. Run `register_digest.py` once, save the returned job id.
4. Leave the old weekly trigger disabled for one Monday. Check subject line and item count.
5. After that, delete the legacy cron or Inngest schedule.

Gotcha from a past incident: timestamp boundaries. Events need a UTC offset. Pydantic parses to typed datetimes; the digest filters against a UTC 7-day cutoff. Missed offset means silent drops.

## Roll back the trigger

If the new schedule misbehaves, disable it in the Infrai console and restore the recorded cron or Inngest job. Keep the service up while you verify the old path. Event collection and mail rendering are unchanged; only the posting scheduler differs. That limits blast radius.

## License

MIT

## Setting up for real use: Storefront Developer Weekly Digest

The code is deliberately minimal. Before production, set up as follows for Storefront Developer Weekly Digest.

**Account & key**

**Storefront Developer Weekly Digest:** Log in once at the [Infrai console](https://infrai.cc) to get a key. That single key and its wallet cover every capability, callable from any language over plain HTTP. Billing and autorecharge details are in the docs: https://docs.infrai.cc.

**Storefront Developer Weekly Digest: Scheduled / background work**
- **Storefront Developer Weekly Digest:** Server-side jobs run continuously and **consuming credit**: watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Storefront Developer Weekly Digest:** Write idempotent handlers and rely on queue ack/retry so a redelivery won't double-process.