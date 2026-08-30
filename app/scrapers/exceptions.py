class ScraperError(Exception):
    """Base exception for scraper failures."""


class ParseError(ScraperError):
    """Raised when a page/response couldn't be parsed as expected (site structure changed)."""


class RateLimitedError(ScraperError):
    """Raised when the target site explicitly rate-limited or blocked the request."""
