import urllib.request
import zlib
from html.parser import HTMLParser

MAX_BYTES = 200_000
TIMEOUT_SECONDS = 5
USER_AGENT = "Mozilla/5.0 (compatible; weekly-menu-bot/1.0)"


def _decode_body(raw):
    """Some sites (e.g. NYT Cooking) gzip the response even though urllib never
    sends Accept-Encoding, and urllib doesn't decompress for us. Sniffing the
    gzip magic bytes rather than trusting the header keeps this working when
    the body was cut off at MAX_BYTES — decompressobj yields whatever it
    could inflate from a truncated stream instead of raising."""
    if raw[:2] == b"\x1f\x8b":
        raw = zlib.decompressobj(zlib.MAX_WBITS | 16).decompress(raw)
    return raw.decode("utf-8", errors="ignore")


class _TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_title = None
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("property") == "og:title" and attrs_dict.get("content"):
                self.og_title = attrs_dict["content"]
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data


class UnfurlService:
    def fetch_title(self, url):
        """Best-effort page title for a recipe link — og:title wins over <title>
        since it's usually the cleaner, human-written one. Returns None on any
        failure (unreachable site, no title present, non-http(s) scheme) rather
        than raising, since a missing title just means falling back to the URL."""
        if not url.startswith(("http://", "https://")):
            return None

        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                html = _decode_body(response.read(MAX_BYTES))
        except Exception:
            return None

        parser = _TitleParser()
        parser.feed(html)
        title = parser.og_title or parser.title
        return title.strip() if title else None
