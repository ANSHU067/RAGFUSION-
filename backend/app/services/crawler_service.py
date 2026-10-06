"""Restricted HTTP crawler with public-address resolution and bounded responses."""

from __future__ import annotations

import asyncio
import re
import socket
from ipaddress import ip_address
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import aiohttp
import anyio
import logging

from app.schemas.website import (
    CrawlDepth,
    CrawledPage,
    WebsiteCrawlRequest,
    WebsiteProcessingConfig,
)


@dataclass
class CrawlResult:
    """Result of a crawl operation."""

    pages: list[CrawledPage]
    base_url: str
    errors: list[str]


class CrawlerError(Exception):
    """Raised when crawling fails."""

    def __init__(self, message: str, code: str = "CRAWL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CrawlerTimeoutError(CrawlerError):
    """Raised when crawling times out."""

    def __init__(self, message: str):
        super().__init__(message, code="CRAWL_TIMEOUT")


class CrawlerValidationError(CrawlerError):
    """Raised when URL validation fails."""

    def __init__(self, message: str):
        super().__init__(message, code="CRAWL_VALIDATION_ERROR")


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CRAWL_LIMITER = anyio.CapacityLimiter(2)
# Azure WireServer is globally classified but exposes platform services.
BLOCKED_PLATFORM_IPS = frozenset({ip_address("168.63.129.16"), ip_address("169.254.169.254")})
logger = logging.getLogger(__name__)


def require_public_ip(host: str) -> None:
    try:
        address = ip_address(host)
    except ValueError as exc:
        raise CrawlerValidationError("Invalid resolved address") from exc
    if address in BLOCKED_PLATFORM_IPS or not address.is_global or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise CrawlerValidationError("Destination is not allowed")
    # Do not permit transition addresses that tunnel to a non-public IPv4 host.
    for embedded in (getattr(address, "ipv4_mapped", None), getattr(address, "sixtofour", None)):
        if embedded is not None:
            require_public_ip(str(embedded))
    if getattr(address, "teredo", None) is not None:
        raise CrawlerValidationError("Destination is not allowed")


class PublicResolver(aiohttp.DefaultResolver):
    """Check the actual addresses handed to the connector, avoiding a second DNS lookup."""

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        results = await super().resolve(host, port, family)
        if not results:
            raise CrawlerValidationError("Host has no public addresses")
        for result in results:
            require_public_ip(result["host"])
        return results


def validate_url(url: str) -> None:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise CrawlerValidationError("Invalid URL format") from exc
    if not parsed.scheme or not parsed.netloc:
        raise CrawlerValidationError("Invalid URL format")
    if parsed.scheme not in ("http", "https"):
        raise CrawlerValidationError("Only HTTP and HTTPS URLs are allowed")
    if not hostname or not parsed.netloc or port == 0 or parsed.username is not None or parsed.password is not None:
        raise CrawlerValidationError("Invalid URL format")
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or "%" in hostname:
        raise CrawlerValidationError("Destination is not allowed")
    try:
        ip_address(hostname)
    except ValueError:
        # Hostnames, including noncanonical numeric IPv4 forms, are checked after DNS resolution.
        return
    require_public_ip(hostname)


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    return urlparse(url1).netloc == urlparse(url2).netloc


def normalize_url(url: str, base_url: str) -> str:
    """Normalize a URL relative to a base URL."""
    return urljoin(base_url, url)


async def fetch_page(
    session: aiohttp.ClientSession,
    url: str,
    timeout_seconds: int,
    follow_redirects: bool,
) -> tuple[int, str | None, str | None, list[str]]:
    """Fetch bounded, uncompressed content. Redirects stay disabled regardless of legacy flags."""
    validate_url(url)
    timeout = aiohttp.ClientTimeout(total=min(timeout_seconds, 30), connect=5, sock_read=10)
    try:
        async with session.get(
            url, timeout=timeout, allow_redirects=False, auto_decompress=False,
            headers={"User-Agent": "RAGFUSION-Bot/1.0", "Accept-Encoding": "identity"},
        ) as response:
            if 300 <= response.status < 400:
                raise CrawlerValidationError("HTTP redirects are disabled")
            if response.headers.get("Content-Encoding", "identity").lower() not in ("", "identity"):
                raise CrawlerValidationError("Compressed responses are not supported")
            if response.content_length is not None and response.content_length > MAX_RESPONSE_BYTES:
                raise CrawlerValidationError("Response exceeds 2 MB limit")
            body = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise CrawlerValidationError("Response exceeds 2 MB limit")
                body.extend(chunk)
            html = body.decode("utf-8", errors="replace")
            links = await anyio.to_thread.run_sync(extract_links, html, url, limiter=CRAWL_LIMITER)
            return response.status, response.headers.get("Content-Type", ""), html, links
    except CrawlerError:
        raise
    except asyncio.TimeoutError as exc:
        raise CrawlerTimeoutError("Request timeout") from exc
    except aiohttp.ClientError as exc:
        raise CrawlerError("Page request failed") from exc


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all links from HTML content."""
    links = []
    # Simple regex for href attributes
    href_pattern = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    for match in href_pattern.finditer(html):
        href = match.group(1).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        normalized = normalize_url(href, base_url)
        parsed = urlparse(normalized)

        # Only keep HTTP/HTTPS links
        if parsed.scheme in ("http", "https"):
            links.append(normalized)

    return list(set(links))  # Deduplicate


async def crawl_website(
    request: WebsiteCrawlRequest, config: WebsiteProcessingConfig
) -> CrawlResult:
    """
    Crawl a website starting from the given URL.

    Only the constrained aiohttp transport is available.
    """
    validate_url(str(request.url))

    base_url = str(request.url)
    urlparse(base_url)

    visited: set[str] = set()
    to_visit: list[str] = [base_url]
    all_pages: list[CrawledPage] = []
    errors: list[str] = []

    # Determine max pages based on crawl depth
    max_pages = request.max_pages
    if request.crawl_depth == CrawlDepth.single:
        max_pages = 1
    elif request.crawl_depth == CrawlDepth.shallow:
        max_pages = min(max_pages, 50)

    # Use aiohttp for initial discovery (faster for static sites)
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False, limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=request.timeout_seconds)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=False, auto_decompress=False) as session:
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)

            if current_url in visited:
                continue

            # Check domain restriction
            if not is_same_domain(current_url, base_url):
                continue

            visited.add(current_url)

            try:
                status_code, content_type, html, links = await fetch_page(
                    session,
                    current_url,
                    request.timeout_seconds,
                    request.follow_redirects,
                )

                if status_code >= 400:
                    errors.append(f"{current_url}: HTTP {status_code}")
                    all_pages.append(
                        CrawledPage(
                            url=current_url,
                            status_code=status_code,
                            content_type=content_type,
                            text_content="",
                            error=f"HTTP {status_code}",
                        )
                    )
                    continue

                # Only process HTML content
                if content_type and "text/html" not in content_type.lower():
                    all_pages.append(
                        CrawledPage(
                            url=current_url,
                            status_code=status_code,
                            content_type=content_type,
                            text_content="",
                            error=f"Non-HTML content type: {content_type}",
                        )
                    )
                    continue

                # Extract text content (basic)
                from app.services.extraction_service import extract_text_from_html

                text_content, metadata = await anyio.to_thread.run_sync(
                    extract_text_from_html, html, current_url, limiter=CRAWL_LIMITER
                )

                page = CrawledPage(
                    url=current_url,
                    status_code=status_code,
                    content_type=content_type,
                    text_content=text_content,
                    metadata=metadata,
                    word_count=len(text_content.split()),
                    character_count=len(text_content),
                    links=links,
                )
                all_pages.append(page)

                # Add new links to crawl queue
                if request.crawl_depth != CrawlDepth.single:
                    for link in links:
                        if link not in visited and is_same_domain(link, base_url):
                            to_visit.append(link)

            except CrawlerTimeoutError:
                errors.append(f"{current_url}: Timeout")
                all_pages.append(
                    CrawledPage(
                        url=current_url,
                        status_code=0,
                        text_content="",
                        error="Request timeout",
                    )
                )
            except CrawlerError as e:
                errors.append(f"{current_url}: {e.message}")
                all_pages.append(
                    CrawledPage(
                        url=current_url,
                        status_code=0,
                        text_content="",
                        error=e.message,
                    )
                )
            except Exception:
                logger.exception("Website extraction failed")
                errors.append("Website extraction failed")
                all_pages.append(
                    CrawledPage(
                        url=current_url,
                        status_code=0,
                        text_content="",
                        error="Website extraction failed",
                    )
                )

    return CrawlResult(
        pages=all_pages,
        base_url=base_url,
        errors=errors,
    )


async def crawl_single_page(url: str, timeout_seconds: int = 30) -> CrawledPage:
    """
    Crawl a single page using aiohttp.

    Useful for quick validation or single-page ingestion.
    """
    validate_url(url)

    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False, limit=1)
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=False, auto_decompress=False) as session:
        try:
            status_code, content_type, html, links = await fetch_page(
                session, url, timeout_seconds, True
            )

            if status_code >= 400:
                return CrawledPage(
                    url=url,
                    status_code=status_code,
                    content_type=content_type,
                    text_content="",
                    error=f"HTTP {status_code}",
                )

            if content_type and "text/html" not in content_type.lower():
                return CrawledPage(
                    url=url,
                    status_code=status_code,
                    content_type=content_type,
                    text_content="",
                    error=f"Non-HTML content type: {content_type}",
                )

            from app.services.extraction_service import extract_text_from_html

            text_content, metadata = await anyio.to_thread.run_sync(
                extract_text_from_html, html, url, limiter=CRAWL_LIMITER
            )

            return CrawledPage(
                url=url,
                status_code=status_code,
                content_type=content_type,
                text_content=text_content,
                metadata=metadata,
                word_count=len(text_content.split()),
                character_count=len(text_content),
                links=links,
            )

        except CrawlerTimeoutError:
            return CrawledPage(
                url=url,
                status_code=0,
                text_content="",
                error="Request timeout",
            )
        except CrawlerError as e:
            return CrawledPage(
                url=url,
                status_code=0,
                text_content="",
                error=e.message,
            )
        except Exception:
            logger.exception("Website extraction failed")
            return CrawledPage(
                url=url,
                status_code=0,
                text_content="",
                error="Website extraction failed",
            )
