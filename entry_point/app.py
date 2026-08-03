import json

from services import ServiceFactory


def lambda_handler(event, context):
    """Expects API Gateway HTTP API (payload format 2.0) proxy events, routed as:
    GET /weeks             -> list every stored week
    GET /weeks/{weekStart} -> fetch one week
    PUT /weeks/{weekStart} -> create or overwrite one week, body = WeekMenu JSON
    """
    sf = ServiceFactory()
    storage_service = sf.get_storage_service()

    method = event["requestContext"]["http"]["method"]
    week_start = (event.get("pathParameters") or {}).get("weekStart")

    if method == "GET" and week_start:
        week = storage_service.get_week(week_start)
        if not week:
            return _response(404, {"message": "Week not found"})
        return _response(200, week)

    if method == "GET":
        return _response(200, storage_service.list_weeks())

    if method == "PUT" and week_start:
        body = json.loads(event.get("body") or "{}")
        body["weekStart"] = week_start
        storage_service.save_week(body)
        return _response(200, body)

    return _response(400, {"message": "Unsupported route"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
