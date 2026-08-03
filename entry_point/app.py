import json

from services import ServiceFactory


def lambda_handler(event, context):
    """Expects a REST API Lambda proxy event, routed as:
    GET /weekly_planner             -> list every stored week
    GET /weekly_planner/{weekStart} -> fetch one week
    PUT /weekly_planner/{weekStart} -> create or overwrite one week, body = WeekMenu JSON
    """
    method = event["httpMethod"]
    week_start = (event.get("pathParameters") or {}).get("weekStart")

    if method == "GET" and week_start:
        storage_service = ServiceFactory().get_storage_service()
        week = storage_service.get_week(week_start)
        if not week:
            return _response(404, {"message": "Week not found"})
        return _response(200, week)

    if method == "GET":
        return _response(200, ServiceFactory().get_storage_service().list_weeks())

    if method == "PUT" and week_start:
        storage_service = ServiceFactory().get_storage_service()
        body = json.loads(event.get("body") or "{}")
        body["weekStart"] = week_start
        storage_service.save_week(body)
        return _response(200, body)

    return _response(400, {"message": "Unsupported route"})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # Proxy integration passes headers through as-is — API Gateway's
            # "Enable CORS" only covers the OPTIONS preflight response, the
            # actual GET/PUT response has to carry this itself or the browser
            # blocks it from JS even though the request succeeded server-side.
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
