import logging
import os
import time
from datetime import date

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.scrapers.exceptions import RateLimitedError, ScraperError

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "cache")


class ScraperHttpClient:
    """Shared HTTP client for all scrapers: consistent User-Agent, timeout,
    retry/backoff on transient failures, inter-request delay, and optional
    on-disk response caching for debugging and offline test fixtures.
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": settings.scraper_user_agent},
            timeout=settings.scraper_timeout_seconds,
            follow_redirects=True,
        )
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = settings.scraper_request_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    @retry(
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=settings.scraper_backoff_factor, min=1, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        reraise=True,
    )
    def _do_get(self, url: str, **kwargs) -> httpx.Response:
        self._throttle()
        response = self._client.get(url, **kwargs)
        self._last_request_at = time.monotonic()

        if response.status_code == 429:
            raise RateLimitedError(f"Rate limited by {url}")
        response.raise_for_status()
        return response

    def get(self, url: str, *, cache_key: str | None = None, **kwargs) -> httpx.Response:
        try:
            response = self._do_get(url, **kwargs)
        except RateLimitedError:
            logger.error("Rate limited fetching %s", url)
            raise
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error fetching %s: %s", url, exc)
            raise ScraperError(f"HTTP error fetching {url}: {exc}") from exc
        except httpx.TransportError as exc:
            logger.error("Transport error fetching %s: %s", url, exc)
            raise ScraperError(f"Transport error fetching {url}: {exc}") from exc

        if cache_key:
            self._cache_response(cache_key, response.text)

        return response

    @staticmethod
    def _cache_response(cache_key: str, content: str) -> None:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            filename = f"{cache_key}_{date.today().isoformat()}.html"
            path = os.path.join(CACHE_DIR, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            logger.warning("Failed to cache response for %s: %s", cache_key, exc)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ScraperHttpClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
