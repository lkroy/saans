"""AWS Lambda entrypoint.

FastAPI runs behind API Gateway (HTTP API) via Mangum. The same function is
also the target of the EventBridge Scheduler rule (daily 05:30 Asia/Kolkata):
scheduled events are detected by their ``source`` (``aws.scheduler`` for
Scheduler, ``aws.events`` for classic rules) and fan out morning bulletins for
every registered school instead of serving HTTP.

When the ``ALERTS_TOPIC_ARN`` env var is set (see infra/template.yaml), each
bulletin is published to the SNS topic; otherwise it is logged so CloudWatch
captures the output.
"""

import json
import os

from mangum import Mangum

from . import advisory, stores
from .main import app

_asgi = Mangum(app)
_TOPIC_ARN = os.environ.get("ALERTS_TOPIC_ARN")


def _is_scheduled_event(event):
    return (
        isinstance(event, dict)
        and event.get("source") in ("aws.scheduler", "aws.events")
    )


def _publish_sns(bulletin: dict):
    import boto3

    win = (bulletin["best_windows"] or [None])[0]
    win_txt = (f"Cleanest {win['start'][11:16]}-{win['end'][11:16]}"
               if win else "No clean window today")
    first_action = (bulletin["checklist"] or [""])[0]

    sms_text = (
        f"Saans {bulletin['level'].upper()} day, {bulletin['school']}: "
        f"AQI {bulletin['aqi_now']} ({bulletin['category']}). "
        f"{win_txt}. {first_action}"
    )[:300]

    email_text = (
        f"Saans morning bulletin — {bulletin['school']} ({bulletin.get('city', '')})\n\n"
        f"{bulletin['headline']}\n{bulletin['detail']}\n\n"
        f"AQI now: {bulletin['aqi_now']} ({bulletin['category']})\n"
        f"Today's peak: AQI {bulletin['peak_today']['aqi']} at {bulletin['peak_today']['at'][11:16]}\n"
        f"{win_txt}\n\nChecklist:\n"
        + "\n".join(f"- {c}" for c in bulletin["checklist"])
    )

    boto3.client("sns").publish(
        TopicArn=_TOPIC_ARN,
        Subject=f"Saans bulletin: {bulletin['school']} — {bulletin['level'].upper()}",
        Message=json.dumps({
            "default": email_text,
            "sms": sms_text,
            "email": email_text,
        }),
        MessageStructure="json",
    )


def _run_daily_bulletins():
    schools = stores.list_all()
    results = []
    for school in schools:
        try:
            adv = advisory.school_advisory(school["lat"], school["lon"])
            bulletin = {
                "school_id": school["id"],
                "school": school["name"],
                "city": school.get("city"),
                "level": adv["level"],
                "headline": adv["headline"],
                "detail": adv["detail"],
                "aqi_now": adv["aqi_now"],
                "category": adv["category"],
                "peak_today": adv["peak_today"],
                "best_windows": adv["best_windows"],
                "checklist": adv["checklist"],
            }
            if _TOPIC_ARN:
                _publish_sns(bulletin)
            else:
                print(f"[saans-bulletin] {json.dumps(bulletin, default=str)}")
            results.append({"school_id": school["id"], "ok": True})
        except Exception as exc:  # one school's failure must not stop the rest
            print(f"[saans-bulletin] FAILED {school['id']}: {exc}")
            results.append(
                {"school_id": school["id"], "ok": False, "error": str(exc)}
            )
    return {"ok": True, "bulletins": results, "count": len(results)}


def handler(event, context):
    if _is_scheduled_event(event):
        return _run_daily_bulletins()
    return _asgi(event, context)
