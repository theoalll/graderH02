"""
Custom security and limit violation exceptions for ptdecoder.
"""

from __future__ import annotations


class PktSecurityError(ValueError):
    """Base exception for ptdecoder security and limit violations."""
    pass


class PktFileSizeExceededError(PktSecurityError):
    """Raised when raw PKT file size exceeds max_file_size limit."""
    pass


class PktDecompressionLimitError(PktSecurityError):
    """Raised when uncompressed XML payload size exceeds max_uncompressed_bytes limit."""
    pass


class PktXmlLimitError(PktSecurityError):
    """Raised when XML element count or nesting depth exceeds safety limits."""
    pass
