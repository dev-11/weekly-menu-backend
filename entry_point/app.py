import json

from services import ServiceFactory


def lambda_handler(event, context):
    """Expects a REST API Lambda proxy event, routed as:
    GET /weekly_planner             -> list every stored week
    GET /weekly_planner/{weekStart} -> fetch one week
    PUT /weekly_planner/{weekStart} -> create or overwrite one week, body = WeekMenu JSON
    GET /weekly_planner/unfurl      -> {"title": ...} for ?url=, or null if unresolved
    GET /weekly_planner/insights    -> pre-computed insights report across all stored weeks
    GET /weekly_planner/recipes     -> every home-cooked dish, with count and last-cooked date

    "resource" (the matched API Gateway resource template, e.g.
    "/weekly_planner/unfurl") disambiguates unfurl/insights/recipes from the
    other two GETs, since neither pathParameters nor the body can do that on
    their own.
    """
    method = event["httpMethod"]
    week_start = (event.get("pathParameters") or {}).get("weekStart")
    resource = event.get("resource")

    if resource == "/weekly_planner/unfurl" and method == "GET":
        url = (event.get("queryStringParameters") or {}).get("url")
        if not url:
            return _response(400, {"message": "Missing url parameter"})
        unfurl_service = ServiceFactory().get_unfurl_service()
        return _response(200, {"title": unfurl_service.fetch_title(url)})

    if resource == "/weekly_planner/insights" and method == "GET":
        weeks = ServiceFactory().get_storage_service().list_weeks()
        insights_service = ServiceFactory().get_insights_service()
        return _response(200, insights_service.build_report(weeks))

    if resource == "/weekly_planner/recipes" and method == "GET":
        weeks = ServiceFactory().get_storage_service().list_weeks()
        insights_service = ServiceFactory().get_insights_service()
        return _response(200, insights_service.get_recipes(weeks))

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
