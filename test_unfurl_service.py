import unittest
from unittest.mock import MagicMock, patch

from services.unfurl_service import UnfurlService


class TestUnfurlService(unittest.TestCase):
    def setUp(self):
        self.service = UnfurlService()

    def test_rejects_non_http_scheme(self):
        self.assertIsNone(self.service.fetch_title("file:///etc/passwd"))

    @patch("services.unfurl_service.urllib.request.urlopen")
    def test_prefers_og_title_over_title_tag(self, mock_urlopen):
        html = (
            b"<html><head>"
            b'<meta property="og:title" content="Sheet-Pan Feta">'
            b"<title>Sheet-Pan Feta Recipe - NYT Cooking</title>"
            b"</head></html>"
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = html

        title = self.service.fetch_title("https://cooking.nytimes.com/recipes/1234")

        self.assertEqual(title, "Sheet-Pan Feta")

    @patch("services.unfurl_service.urllib.request.urlopen")
    def test_falls_back_to_title_tag(self, mock_urlopen):
        html = b"<html><head><title>Just a Title</title></head></html>"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = html

        title = self.service.fetch_title("https://example.com/recipe")

        self.assertEqual(title, "Just a Title")

    @patch("services.unfurl_service.urllib.request.urlopen")
    def test_returns_none_when_no_title_present(self, mock_urlopen):
        html = b"<html><head></head><body>no title here</body></html>"
        mock_urlopen.return_value.__enter__.return_value.read.return_value = html

        self.assertIsNone(self.service.fetch_title("https://example.com/recipe"))

    @patch("services.unfurl_service.urllib.request.urlopen")
    def test_returns_none_on_fetch_failure(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("unreachable")

        self.assertIsNone(self.service.fetch_title("https://example.com/recipe"))


if __name__ == "__main__":
    unittest.main()
