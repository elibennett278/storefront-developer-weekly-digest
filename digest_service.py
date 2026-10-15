"""Build and deliver the weekly storefront engineering digest."""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, field_validator


class TimestampedEvent(BaseModel):
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a UTC offset")
        return value


class BuildEvent(TimestampedEvent):
    project: str
    status: Literal["passed", "failed"]
    revision: str


class ReleaseOperation(TimestampedEvent):
    storefront: str
    version: str
    action: Literal["deployed", "rolled_back"]


class Diagnostic(TimestampedEvent):
    service: str
    severity: Literal["info", "warning", "critical"]
    summary: str


class DigestWindow(BaseModel):
    builds: list[BuildEvent]
    releases: list[ReleaseOperation]
    diagnostics: list[Diagnostic]


class DigestResult(BaseModel):
    subject: str
    body: str
    included_items: int


def compose_digest(window: DigestWindow, now: datetime) -> DigestResult:
    """Include the last seven days, putting checkout risks before routine activity."""
    cutoff = now.astimezone(timezone.utc) - timedelta(days=7)
    failed = [
        item
        for item in window.builds
        if cutoff <= item.occurred_at <= now and item.status == "failed"
    ]
    releases = [item for item in window.releases if cutoff <= item.occurred_at <= now]
    diagnostics = [
        item
        for item in window.diagnostics
        if cutoff <= item.occurred_at <= now and item.severity in {"warning", "critical"}
    ]

    lines = ["Storefront engineering, last 7 days", ""]
    lines.append(f"Builds needing attention ({len(failed)})")
    lines.extend(f"- {item.project} at {item.revision}: {item.status}" for item in failed)
    lines.append("")
    lines.append(f"Release operations ({len(releases)})")
    lines.extend(
        f"- {item.storefront} {item.version}: {item.action}" for item in releases
    )
    lines.append("")
    lines.append(f"Developer diagnostics ({len(diagnostics)})")
    lines.extend(
        f"- [{item.severity}] {item.service}: {item.summary}" for item in diagnostics
    )
    included = len(failed) + len(releases) + len(diagnostics)
    if included == 0:
        lines.append("- No action items this week.")
    return DigestResult(
        subject=f"Storefront developer digest: {included} items",
        body="\n".join(lines),
        included_items=included,
    )


def deliver_digest(result: DigestResult) -> None:
    message = EmailMessage()
    message["Subject"] = result.subject
    message["From"] = os.environ["DIGEST_FROM"]
    message["To"] = os.environ["DIGEST_TO"]
    message.set_content(result.body)
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def load_window(path: Path) -> DigestWindow:
    return DigestWindow.model_validate(json.loads(path.read_text(encoding="utf-8")))


app = FastAPI(title="Storefront developer digest")


@app.post("/digest/weekly", response_model=DigestResult)
def send_weekly_digest() -> DigestResult:
    window = load_window(Path(os.environ.get("DIGEST_EVENTS_FILE", "events.json")))
    result = compose_digest(window, datetime.now(timezone.utc))
    deliver_digest(result)
    return result
