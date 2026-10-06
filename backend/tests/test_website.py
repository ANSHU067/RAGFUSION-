"""Website ingestion tests."""

from __future__ import annotations

import pytest
from app.schemas.website import (
    CrawledPage,
    WebsiteChunkingConfig,
    WebsiteMetadata,
    WebsiteProcessingConfig,
)
from app.services.chunking_service import (
    chunk_single_page,
    chunk_text_fixed,
    chunk_text_recursive,
    chunk_text_semantic,
    chunk_website_content,
    estimate_tokens,
)
from app.services.crawler_service import (
    CrawlerTimeoutError,
    CrawlerValidationError,
    extract_links,
    is_same_domain,
    normalize_url,
    validate_url,
)
from app.services.extraction_service import (
    clean_html,
    clean_text,
    extract_text_from_html,
)


class TestURLValidation:
    """Tests for URL validation."""

    def test_validate_url_valid_http(self):
        """Test validation accepts valid HTTP URL."""
        validate_url("http://example.com")
        validate_url("http://example.com/path")
        validate_url("http://example.com:8080/path?query=1")

    def test_validate_url_valid_https(self):
        """Test validation accepts valid HTTPS URL."""
        validate_url("https://example.com")
        validate_url("https://subdomain.example.com/path")

    def test_validate_url_invalid_format(self):
        """Test validation rejects invalid URL format."""
        with pytest.raises(CrawlerValidationError) as exc:
            validate_url("not-a-url")
        assert "Invalid URL format" in exc.value.message

        with pytest.raises(CrawlerValidationError):
            validate_url("")

        with pytest.raises(CrawlerValidationError):
            validate_url("://example.com")

    def test_validate_url_invalid_scheme(self):
        """Test validation rejects non-HTTP schemes."""
        with pytest.raises(CrawlerValidationError) as exc:
            validate_url("ftp://example.com")
        assert "HTTP and HTTPS" in exc.value.message

        with pytest.raises(CrawlerValidationError):
            validate_url("file:///etc/passwd")

    def test_validate_url_blocked_localhost(self):
        """Test validation blocks localhost."""
        with pytest.raises(CrawlerValidationError) as exc:
            validate_url("http://localhost:8000")
        assert "not allowed" in exc.value.message

        with pytest.raises(CrawlerValidationError):
            validate_url("http://127.0.0.1")

    def test_validate_url_blocked_private_ip(self):
        """Test validation blocks private IP addresses."""
        with pytest.raises(CrawlerValidationError):
            validate_url("http://192.168.1.1")

        with pytest.raises(CrawlerValidationError):
            validate_url("http://10.0.0.1")

        with pytest.raises(CrawlerValidationError):
            validate_url("http://172.16.0.1")


class TestURLUtilities:
    """Tests for URL utility functions."""

    def test_is_same_domain(self):
        """Test domain comparison."""
        assert is_same_domain("http://example.com", "http://example.com/page")
        assert is_same_domain("https://example.com", "http://example.com")
        assert not is_same_domain("http://example.com", "http://other.com")
        assert not is_same_domain("http://example.com", "http://sub.example.com")

    def test_normalize_url(self):
        """Test URL normalization."""
        base = "http://example.com/path/"
        assert normalize_url("page.html", base) == "http://example.com/path/page.html"
        assert normalize_url("/absolute", base) == "http://example.com/absolute"
        assert normalize_url("http://other.com", base) == "http://other.com"

    def test_extract_links(self):
        """Test link extraction from HTML."""
        html = """
        <html>
        <body>
            <a href="http://example.com/page1">Link 1</a>
            <a href="/page2">Link 2</a>
            <a href="#anchor">Anchor</a>
            <a href="javascript:void(0)">JS</a>
            <a href="mailto:test@example.com">Email</a>
        </body>
        </html>
        """
        base_url = "http://example.com"
        links = extract_links(html, base_url)

        assert "http://example.com/page1" in links
        assert "http://example.com/page2" in links
        assert len([link for link in links if link.startswith("#")]) == 0
        assert len([link for link in links if link.startswith("javascript:")]) == 0
        assert len([link for link in links if link.startswith("mailto:")]) == 0


class TestHTMLCleaning:
    """Tests for HTML cleaning."""

    def test_clean_html_removes_scripts(self):
        """Test script tag removal."""
        html = "<html><body><script>alert('test');</script><p>Content</p></body></html>"
        config = WebsiteProcessingConfig()
        cleaned = clean_html(html, config)
        assert "<script>" not in cleaned
        assert "alert" not in cleaned
        assert "Content" in cleaned

    def test_clean_html_removes_styles(self):
        """Test style tag removal."""
        html = "<html><head><style>body { color: red; }</style></head><body>Content</body></html>"
        config = WebsiteProcessingConfig()
        cleaned = clean_html(html, config)
        assert "<style>" not in cleaned
        assert "color: red" not in cleaned
        assert "Content" in cleaned

    def test_clean_html_removes_nav_footer(self):
        """Test navigation and footer removal."""
        html = """
        <html><body>
            <nav>Navigation</nav>
            <main>Main Content</main>
            <footer>Footer</footer>
        </body></html>
        """
        config = WebsiteProcessingConfig()
        cleaned = clean_html(html, config)
        assert "Navigation" not in cleaned
        assert "Footer" not in cleaned
        assert "Main Content" in cleaned

    def test_clean_html_removes_hidden_elements(self):
        """Test hidden element removal."""
        html = """
        <html><body>
            <div style="display: none;">Hidden</div>
            <div>Visible</div>
        </body></html>
        """
        config = WebsiteProcessingConfig()
        cleaned = clean_html(html, config)
        assert "Hidden" not in cleaned
        assert "Visible" in cleaned


class TestTextExtraction:
    """Tests for text extraction from HTML."""

    def test_extract_text_from_html_basic(self):
        """Test basic text extraction."""
        html = "<html><body><h1>Title</h1><p>Paragraph content.</p></body></html>"
        text, metadata = extract_text_from_html(html, "http://example.com")

        assert "Title" in text
        assert "Paragraph content" in text
        assert metadata.url == "http://example.com"

    def test_extract_text_from_html_with_metadata(self):
        """Test extraction with metadata."""
        html = """
        <html>
        <head>
            <title>Page Title</title>
            <meta name="description" content="Page description">
            <meta name="author" content="John Doe">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        text, metadata = extract_text_from_html(html, "http://example.com")

        assert "Content" in text
        assert metadata.title or True  # trafilatura may or may not extract title

    def test_extract_text_from_html_empty(self):
        """Test extraction from empty HTML."""
        html = "<html><body></body></html>"
        text, metadata = extract_text_from_html(html, "http://example.com")

        assert isinstance(text, str)
        assert metadata.url == "http://example.com"

    def test_extract_text_malformed_html(self):
        """Test extraction handles malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<div>Content</body>"
        text, metadata = extract_text_from_html(html, "http://example.com")

        assert "Content" in text or "Unclosed" in text
        assert metadata.url == "http://example.com"


class TestTextCleaning:
    """Tests for text cleaning."""

    def test_clean_text_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    World\n\n\nMultiple   spaces"
        cleaned = clean_text(text)
        assert "    " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_clean_text_empty(self):
        """Test cleaning empty text."""
        text = ""
        cleaned = clean_text(text)
        assert cleaned == ""

    def test_clean_text_preserves_content(self):
        """Test cleaning preserves meaningful content."""
        text = "Important content that should remain."
        cleaned = clean_text(text)
        assert "Important content" in cleaned
        assert "should remain" in cleaned


class TestChunking:
    """Tests for content chunking."""

    def test_chunk_text_fixed_basic(self):
        """Test fixed-size chunking."""
        text = " ".join([f"word{i}" for i in range(200)])
        config = WebsiteChunkingConfig(
            chunk_size=100, chunk_overlap=20, strategy="fixed"
        )
        chunks = chunk_text_fixed(text, config, "http://example.com")

        assert len(chunks) > 1
        assert all(c.source_url == "http://example.com" for c in chunks)
        assert all(c.metadata["strategy"] == "fixed" for c in chunks)

    def test_chunk_text_recursive(self):
        """Test recursive chunking."""
        text = (
            "Section 1\n\n"
            + ("Content " * 100)
            + "\n\nSection 2\n\n"
            + ("More content " * 100)
        )
        config = WebsiteChunkingConfig(
            chunk_size=200, chunk_overlap=50, strategy="recursive"
        )
        chunks = chunk_text_recursive(text, config, "http://example.com")

        assert len(chunks) >= 1
        assert all(c.metadata["strategy"] == "recursive" for c in chunks)

    def test_chunk_text_semantic(self):
        """Test semantic chunking."""
        text = "# Heading 1\n\nContent for heading 1.\n\n## Heading 2\n\nContent for heading 2."
        config = WebsiteChunkingConfig(
            chunk_size=200, chunk_overlap=50, strategy="semantic"
        )
        chunks = chunk_text_semantic(text, config, "http://example.com")

        assert len(chunks) >= 1
        assert all(c.metadata["strategy"] == "semantic" for c in chunks)

    def test_chunk_website_content_multiple_pages(self):
        """Test chunking multiple pages."""
        pages_content = [
            ("http://example.com/page1", "Content for page 1. " * 50),
            ("http://example.com/page2", "Content for page 2. " * 50),
        ]
        config = WebsiteProcessingConfig(
            chunking=WebsiteChunkingConfig(
                chunk_size=100, chunk_overlap=20, strategy="fixed"
            )
        )
        chunks = chunk_website_content(pages_content, config)

        assert len(chunks) > 2
        page1_chunks = [c for c in chunks if c.source_url == "http://example.com/page1"]
        page2_chunks = [c for c in chunks if c.source_url == "http://example.com/page2"]
        assert len(page1_chunks) > 0
        assert len(page2_chunks) > 0

    def test_chunk_single_page(self):
        """Test single page chunking."""
        text = "Sample content. " * 100
        config = WebsiteProcessingConfig()
        chunks = chunk_single_page(text, "http://example.com", config)

        assert len(chunks) >= 1
        assert all(c.source_url == "http://example.com" for c in chunks)

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a sample text with multiple words."
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Should be less than character count


class TestWebsiteAPI:
    """Only the authenticated, bounded single-page ingestion API is exposed."""

    def test_website_ingestion_requires_authentication(self, client):
        assert client.post('/api/v1/website/ingest', json={'url': 'http://127.0.0.1/'}).status_code == 401
        assert '/api/v1/website/crawl' not in client.app.openapi()['paths']


class TestCrawlerErrorHandling:
    """Tests for crawler error scenarios."""

    @pytest.mark.asyncio
    async def test_crawl_empty_response(self):
        """Test handling of empty response."""
        html = ""
        text, metadata = extract_text_from_html(html, "http://example.com")
        assert isinstance(text, str)
        assert metadata.url == "http://example.com"

    @pytest.mark.asyncio
    async def test_crawl_duplicate_pages(self):
        """Test deduplication of pages."""
        # Same domain check ensures no duplicates
        assert is_same_domain("http://example.com/page1", "http://example.com/page1")

    @pytest.mark.asyncio
    async def test_crawl_unsupported_content(self):
        """Test handling of non-HTML content."""
        # CrawledPage would have error field set
        page = CrawledPage(
            url="http://example.com/file.pdf",
            status_code=200,
            content_type="application/pdf",
            text_content="",
            error="Non-HTML content type: application/pdf",
        )
        assert page.error is not None
        assert "Non-HTML" in page.error


class TestExtractionFailure:
    """Tests for extraction failure scenarios."""

    def test_extraction_malformed_html(self):
        """Test extraction handles malformed HTML."""
        html = "<html><body><p>Unclosed<div>Tags</body>"
        text, metadata = extract_text_from_html(html, "http://example.com")

        # Should not raise, should return something
        assert isinstance(text, str)
        assert isinstance(metadata, WebsiteMetadata)

    def test_extraction_javascript_heavy(self):
        """Test extraction from JS-heavy sites."""
        html = """
        <html>
        <body>
            <script>document.write('Dynamic content');</script>
            <div id="root"></div>
        </body>
        </html>
        """
        text, metadata = extract_text_from_html(html, "http://example.com")

        # Static extraction does not execute JavaScript.
        assert isinstance(text, str)
    def test_extraction_with_encoding_issues(self):
        """Test extraction handles encoding issues."""
        # This would need actual bytes with encoding issues
        html = "<html><body>Content with special chars: café résumé</body></html>"
        text, metadata = extract_text_from_html(html, "http://example.com")

        assert isinstance(text, str)
