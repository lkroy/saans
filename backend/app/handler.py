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


def _publish_sns(bulletin: dict, update: bool = False):
    """Publish a bulletin; ``update=True`` marks it as a material-change alert."""
    import boto3

    win = (bulletin["best_windows"] or [None])[0]
    win_txt = (f"Cleanest {win['start'][11:16]}-{win['end'][11:16]}"
               if win else "No clean window in school hours")
    first_action = (bulletin["checklist"] or [""])[0]
    kind = "UPDATE" if update else bulletin["action_label"].upper()

    sms_text = (
        f"Saans {kind}, {bulletin['school']}: "
        f"AQI {bulletin['aqi_now']} ({bulletin['category']}). "
        f"{win_txt}. {first_action}"
    )[:300]

    change_line = ""
    if update and bulletin.get("change"):
        c = bulletin["change"]
        change_line = (f"\nWhat changed: {c['from_label']} → {c['to_label']} "
                       f"(AQI now {c['aqi_now']}, 6h peak {c['peak_6h']}).\n")

    email_text = (
        f"Saans {'update' if update else 'morning bulletin'} — "
        f"{bulletin['school']} ({bulletin.get('city', '')})\n"
        f"{change_line}\n"
        f"{bulletin['headline']}\n{bulletin['detail']}\n\n"
        f"AQI now: {bulletin['aqi_now']} ({bulletin['category']}, indicative)\n"
        f"Today's peak: AQI {bulletin['peak_today']['aqi']} at {bulletin['peak_today']['at'][11:16]}\n"
        f"{win_txt}\n\nChecklist:\n"
        + "\n".join(f"- {c}" for c in bulletin["checklist"])
        + f"\n\n{bulletin['disclaimer']}"
    )

    boto3.client("sns").publish(
        TopicArn=_TOPIC_ARN,
        Subject=f"Saans {'update' if update else 'bulletin'}: {bulletin['school']} — {bulletin['action_label']}",
        Message=json.dumps({
            "default": email_text,
            "sms": sms_text,
            "email": email_text,
        }),
        MessageStructure="json",
    )


def _material_change(school, adv):
    """Decide whether the new advisory materially changes the last bulletin.

    Material = the school-day call level changed. Returns a change dict or
    None. Dedupe: at most one update per school per day unless the level
    worsens (escalation always notifies).
    """
    from datetime import datetime
    from .data import IST
    last = school.get("last_bulletin") or {}
    today = datetime.now(IST).date().isoformat()
    if last.get("level") == adv["level"]:
        return None  # no material change
    if not last.get("level"):
        return None  # first bulletin is the baseline, not an "update"
    if last.get("date") == today and last.get("update_sent"):
        order = ["clear", "caution", "indoor", "severe"]
        try:
            worsened = order.index(adv["level"]) > order.index(last["level"])
        except ValueError:
            worsened = False
        if not worsened:
            return None  # already updated today; don't spam
    return {
        "from_level": last["level"],
        "from_label": last.get("action_label", last["level"]),
        "to_level": adv["level"],
        "to_label": adv["action_label"],
        "aqi_now": adv["aqi_now"],
        "peak_6h": adv["peak_6h"]["aqi"],
    }


def _run_daily_bulletins():
    from datetime import datetime
    from .data import IST
    schools = stores.list_all()
    today = datetime.now(IST).date().isoformat()
    results = []
    for school in schools:
        try:
            # School-aware advisory: windows respect this school's hours.
            adv = advisory.school_advisory(school["lat"], school["lon"],
                                           school=school)
            bulletin = {
                "school_id": school["id"],
                "school": school["name"],
                "city": school.get("city"),
                "level": adv["level"],
                "action_label": adv["action_label"],
                "headline": adv["headline"],
                "detail": adv["detail"],
                "aqi_now": adv["aqi_now"],
                "category": adv["category"],
                "peak_today": adv["peak_today"],
                "best_windows": adv["best_windows"],
                "windows_note": adv["windows_note"],
                "checklist": adv["checklist"],
                "disclaimer": adv["disclaimer"],
                "evidence": adv["evidence"],
                "generated_at": adv["generated_at"],
            }
            change = _material_change(school, adv)
            bulletin["change"] = change
            if _TOPIC_ARN:
                _publish_sns(bulletin, update=bool(change))
            else:
                print(f"[saans-bulletin] {json.dumps(bulletin, default=str)}")
            stores.set_last_bulletin(school["id"], {
                "date": today,
                "level": adv["level"],
                "action_label": adv["action_label"],
                "generated_at": adv["generated_at"],
                "update_sent": bool(change),
            })
            results.append({"school_id": school["id"], "ok": True,
                            "update": bool(change)})
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
