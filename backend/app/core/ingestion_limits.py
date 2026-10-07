"""Hard ceilings shared by document transport, validation, and processing."""

MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024
UPLOAD_READ_BYTES = 64 * 1024
MAX_DOCUMENT_CHUNKS = 2000
MAX_EXTRACTED_CHARACTERS = 8_000_000
MAX_DOCX_EXPANDED_BYTES = 32 * 1024 * 1024
MAX_DOCX_ENTRIES = 2048
MAX_PDF_PAGES = 1000


def document_size_limit(configured_mb: int = 15) -> int:
    """Operators may lower the limit, but cannot raise the hard ceiling."""
    return min(MAX_DOCUMENT_BYTES, configured_mb * 1024 * 1024)
