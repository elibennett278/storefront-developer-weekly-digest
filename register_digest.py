"""Register the weekly digest endpoint with Infrai cron."""

import os

import infrai


def register() -> str:
    task_url = os.environ["DIGEST_TASK_URL"]
    data = infrai.cron.create(
        cron_expr="0 9 * * 1",
        task=task_url,
        idempotency_key="storefront-developer-digest-v1",
    )
    return str(data["job_id"])


if __name__ == "__main__":
    print(f"Scheduled weekly digest: {register()}")
