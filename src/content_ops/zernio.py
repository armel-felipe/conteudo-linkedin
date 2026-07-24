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
    """Flattened posts with the raw API responses retained by page."""

    def __init__(self, posts: list[dict[str, Any]], pages: list[Any]):
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
        raw_pages: list[Any] = []
        page = 1

        while True:
            payload = self._get_page(account_id, page)
            posts = self._posts_from_payload(payload)
            raw_pages.append(payload)
            all_posts.extend(posts)
            if len(posts) < 100:
                return ExternalPosts(all_posts, raw_pages)
            page += 1

    def _get_page(self, account_id: str, page: int) -> Any:
        query = urlencode(
            {"source": "external", "accountId": account_id, "page": page, "limit": 100}
        )
        request = Request(
            f"{self.base_url}/api/v1/posts?{query}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with self._opener(request) as response:
                body = response.read()
        except HTTPError as error:
            raise ZernioError(error.code, self._http_error_message(error)) from error
        except URLError as error:
            raise ZernioError(0, str(error.reason)) from error

        try:
            return json.loads(body.decode("utf-8"))
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
        try:
            body = error.read().decode("utf-8")
            payload = json.loads(body)
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("error")
                if isinstance(message, str):
                    return message
            return body or error.reason
        except (UnicodeDecodeError, json.JSONDecodeError):
            return error.reason
