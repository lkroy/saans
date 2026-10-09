"""AWS Lambda entrypoint.

FastAPI runs behind API Gateway (HTTP API) via Mangum. The same function is
also the target of the EventBridge Scheduler rule (daily 05:30 Asia/Kolkata):
scheduled events are detected by their ``source`` and fan out morning
bulletins for every registered school instead of serving HTTP.

In the SAM deploy, bulletins can be published to the SNS topic (see
infra/template.yaml); here we log them so CloudWatch captures the output.
"""

from mangum import Mangum

from . import advisory, stores
from .main import app

_asgi = Mangum(app)


def _is_scheduled_event(event):
    return isinstance(event, dict) and event.get("source") == "aws.events"


def _run_daily_bulletins():
    schools = stores.list_all()
    results = []
    for school in schools:
        try:
            adv = advisory.school_advisory(school["lat"], school["lon"])
            bulletin = {
                "school_id": school["id"],
                "school": school["name"],
                "level": adv["level"],
                "headline": adv["headline"],
                "aqi_now": adv["aqi_now"],
                "peak_today": adv["peak_today"],
                "checklist": adv["checklist"],
            }
            # In SAM: publish `bulletin` to the SNS alerts topic here.
            print(f"[saans-bulletin] {bulletin}")
            results.append({"school_id": school["id"], "ok": True})
        except Exception as exc:  # one school's failure must not stop the rest
            print(f"[saans-bulletin] FAILED {school['id']}: {exc}")
            results.append({"school_id": school["id"], "ok": False,
                            "error": str(exc)})
    return {"ok": True, "bulletins": results, "count": len(results)}


def handler(event, context):
    if _is_scheduled_event(event):
        return _run_daily_bulletins()
    return _asgi(event, context)
