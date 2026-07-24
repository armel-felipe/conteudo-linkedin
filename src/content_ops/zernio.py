"""Read-only client for importing external posts from Zernio."""

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ZernioError(RuntimeError):
    """An unsuccessful or malformed response from the Zernio API."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"Zernio request failed ({status}): {message}")


class ExternalPosts(list[dict[str, Any]]):
    """Flattened parsed posts with raw HTTP response bytes retained by page."""

    def __init__(self, posts: list[dict[str, Any]], pages: list[bytes]):
        super().__init__(posts)
        self.pages = pages


class ZernioClient:
    """Fetch external posts only; this client intentionally has no write methods."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.zernio.com",
        opener: Callable[[Request], Any] = urlopen,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._opener = opener

    def list_external_posts(self, account_id: str) -> ExternalPosts:
        """Return all external posts for an account, fetching 100 at a time."""
        all_posts: list[dict[str, Any]] = []
        raw_pages: list[bytes] = []
        page = 1

        while True:
            payload, raw_page = self._get_page(account_id, page)
            posts = self._posts_from_payload(payload)
            raw_pages.append(raw_page)
            all_posts.extend(posts)
            if len(posts) < 100:
                return ExternalPosts(all_posts, raw_pages)
            page += 1

    def _get_page(self, account_id: str, page: int) -> tuple[Any, bytes]:
        query = urlencode(
            {"source": "external", "accountId": account_id, "page": page, "limit": 100}
        )
        request = Request(
            f"{self.base_url}/api/v1/posts?{query}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        request_error: tuple[int, str] | None = None
        try:
            with self._opener(request) as response:
                body = response.read()
        except HTTPError as error:
            request_error = (error.code, self._http_error_message(error))
        except URLError:
            request_error = (0, "Network error")

        if request_error is not None:
            raise ZernioError(*request_error)

        try:
            return json.loads(body.decode("utf-8")), body
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ZernioError(200, "Invalid JSON response") from error

    @staticmethod
    def _posts_from_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list) and all(isinstance(post, dict) for post in payload):
            return payload
        if isinstance(payload, dict):
            for key in ("posts", "data", "results"):
                posts = payload.get(key)
                if isinstance(posts, list) and all(isinstance(post, dict) for post in posts):
                    return posts
        raise ZernioError(200, "Invalid JSON response")

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        return f"HTTP {error.code} error"
