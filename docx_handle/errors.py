from __future__ import annotations


class DocxHandleError(RuntimeError):
    """Base error for the service."""


class BadRequestError(DocxHandleError):
    """Raised for invalid HTTP input."""


class WordAutomationUnavailableError(DocxHandleError):
    """Raised when Word COM cannot be initialized on the host."""


class DocumentProcessingError(DocxHandleError):
    """Raised when document cleanup fails."""

