import json
import unittest
from unittest.mock import MagicMock, patch

from entry_point import app


def _event(method, week_start=None, body=None, resource=None, query=None):
    return {
        "httpMethod": method,
        "resource": resource,
        "pathParameters": {"weekStart": week_start} if week_start else None,
        "queryStringParameters": query,
        "body": json.dumps(body) if body is not None else None,
    }


class TestEntryPoint(unittest.TestCase):
    @patch("entry_point.app.ServiceFactory")
    def test_get_week_found(self, mock_factory):
        storage = MagicMock()
        storage.get_week.return_value = {"weekStart": "2026-07-27"}
        mock_factory.return_value.get_storage_service.return_value = storage

        result = app.lambda_handler(_event("GET", "2026-07-27"), None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"]), {"weekStart": "2026-07-27"})

    @patch("entry_point.app.ServiceFactory")
    def test_get_week_not_found(self, mock_factory):
        storage = MagicMock()
        storage.get_week.return_value = None
        mock_factory.return_value.get_storage_service.return_value = storage

        result = app.lambda_handler(_event("GET", "2026-07-27"), None)

        self.assertEqual(result["statusCode"], 404)

    @patch("entry_point.app.ServiceFactory")
    def test_list_weeks(self, mock_factory):
        storage = MagicMock()
        storage.list_weeks.return_value = [{"weekStart": "2026-07-27"}]
        mock_factory.return_value.get_storage_service.return_value = storage

        result = app.lambda_handler(_event("GET"), None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"]), [{"weekStart": "2026-07-27"}])

    @patch("entry_point.app.ServiceFactory")
    def test_save_week(self, mock_factory):
        storage = MagicMock()
        mock_factory.return_value.get_storage_service.return_value = storage

        result = app.lambda_handler(
            _event("PUT", "2026-07-27", {"days": [], "weekendDessert": {}}), None
        )

        storage.save_week.assert_called_once_with(
            {"days": [], "weekendDessert": {}, "weekStart": "2026-07-27"}
        )
        self.assertEqual(result["statusCode"], 200)

    def test_unsupported_route(self):
        result = app.lambda_handler(_event("DELETE"), None)

        self.assertEqual(result["statusCode"], 400)

    @patch("entry_point.app.ServiceFactory")
    def test_unfurl(self, mock_factory):
        unfurl = MagicMock()
        unfurl.fetch_title.return_value = "Sheet-Pan Baked Feta With Broccolini"
        mock_factory.return_value.get_unfurl_service.return_value = unfurl

        result = app.lambda_handler(
            _event(
                "GET",
                resource="/weekly_planner/unfurl",
                query={"url": "https://cooking.nytimes.com/recipes/1234"},
            ),
            None,
        )

        unfurl.fetch_title.assert_called_once_with("https://cooking.nytimes.com/recipes/1234")
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(
            json.loads(result["body"]), {"title": "Sheet-Pan Baked Feta With Broccolini"}
        )

    def test_unfurl_missing_url(self):
        result = app.lambda_handler(
            _event("GET", resource="/weekly_planner/unfurl", query=None), None
        )

        self.assertEqual(result["statusCode"], 400)
