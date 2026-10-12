"""
ptdecoder - Platform-agnostic Python library for decoding Cisco Packet Tracer (.pkt/.pka/.xml) files.

Acknowledgment & Citation:
We express our sincere thanks and appreciation to the creators and maintainers of
Packet Tracer Converter (https://pt-convert.podik.cz/) for reverse-engineering the Twofish-EAX
cryptographic specification and original implementation.
"""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import BinaryIO

from ptdecoder.exceptions import (
    PktDecompressionLimitError,
    PktFileSizeExceededError,
    PktSecurityError,
    PktXmlLimitError,
)
from ptdecoder.crypto import decrypt_pkt
from ptdecoder.models import (
    AclRule,
    Connection,
    Device,
    DhcpPool,
    Interface,
    NatPool,
    NatRule,
    OspfConfig,
    OspfNetwork,
    PduItem,
    PduScenario,
    PktDocument,
    PktMetadata,
    RouterConfig,
    StaticRoute,
    TopologyNote,
    WirelessConfig,
)
from ptdecoder.parser import parse_pkt_stream

__version__ = "1.0.0"
__author__ = "ptdecoder Maintainers"
__citation__ = "Packet Tracer Converter — https://pt-convert.podik.cz/"


def parse_pkt(
    source: str | Path | bytes | BinaryIO,
    file_name: str | None = None,
    max_file_size: int | None = 50_000_000,
    max_uncompressed_bytes: int | None = 100_000_000,
    max_xml_elements: int | None = 500_000,
    max_xml_depth: int | None = 100,
    max_text_length: int | None = 10_000_000,
) -> PktDocument:
    """
    Synchronously decodes and parses a Packet Tracer (.pkt/.pka/.xml) file into a structured PktDocument object.

    Args:
        source: File path, bytes, or open BinaryIO stream.
        file_name: Optional file name override.
        max_file_size: Maximum allowed raw input file size in bytes (default: 50MB). Pass None to disable.
        max_uncompressed_bytes: Maximum allowed uncompressed XML size in bytes (default: 100MB). Pass None to disable.
        max_xml_elements: Maximum allowed XML elements (default: 500k). Pass None to disable.
        max_xml_depth: Maximum allowed XML nesting depth (default: 100). Pass None to disable.
        max_text_length: Maximum allowed character data length per node (default: 10MB). Pass None to disable.

    Returns:
        PktDocument object graph.
    """
    return parse_pkt_stream(
        source,
        file_name=file_name,
        max_file_size=max_file_size,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_xml_elements=max_xml_elements,
        max_xml_depth=max_xml_depth,
        max_text_length=max_text_length,
    )


async def parse_pkt_async(
    source: str | Path | bytes | BinaryIO,
    file_name: str | None = None,
    max_file_size: int | None = 50_000_000,
    max_uncompressed_bytes: int | None = 100_000_000,
    max_xml_elements: int | None = 500_000,
    max_xml_depth: int | None = 100,
    max_text_length: int | None = 10_000_000,
) -> PktDocument:
    """
    Asynchronously decodes and parses a Packet Tracer (.pkt/.pka/.xml) file.
    Offloads CPU-bound Twofish-EAX decryption and SAX parsing to a worker thread
    to keep the asyncio event loop 100% unblocked under heavy concurrency.

    Args:
        source: File path, bytes, or open BinaryIO stream.
        file_name: Optional file name override.
        max_file_size: Maximum allowed raw input file size in bytes (default: 50MB). Pass None to disable.
        max_uncompressed_bytes: Maximum allowed uncompressed XML size in bytes (default: 100MB). Pass None to disable.
        max_xml_elements: Maximum allowed XML elements (default: 500k). Pass None to disable.
        max_xml_depth: Maximum allowed XML nesting depth (default: 100). Pass None to disable.
        max_text_length: Maximum allowed character data length per node (default: 10MB). Pass None to disable.

    Returns:
        PktDocument object graph.
    """
    return await asyncio.to_thread(
        parse_pkt_stream,
        source,
        file_name,
        max_file_size,
        max_uncompressed_bytes,
        max_xml_elements,
        max_xml_depth,
        max_text_length,
    )


async def decrypt_pkt_async(
    source: str | Path | bytes | BinaryIO,
    max_file_size: int | None = 50_000_000,
    max_uncompressed_bytes: int | None = 100_000_000,
) -> bytes:
    """
    Asynchronously decodes a Packet Tracer (.pkt/.pka) file into raw uncompressed XML bytes.

    Args:
        source: File path, bytes, or open BinaryIO stream.
        max_file_size: Maximum allowed raw input file size in bytes (default: 50MB). Pass None to disable.
        max_uncompressed_bytes: Maximum allowed uncompressed XML size in bytes (default: 100MB). Pass None to disable.

    Returns:
        Uncompressed XML bytes.
    """
    return await asyncio.to_thread(decrypt_pkt, source, max_file_size, max_uncompressed_bytes)


__all__ = [
    "parse_pkt",
    "parse_pkt_async",
    "decrypt_pkt",
    "decrypt_pkt_async",
    "PktDocument",
    "Device",
    "Interface",
    "Connection",
    "RouterConfig",
    "AclRule",
    "NatPool",
    "NatRule",
    "DhcpPool",
    "OspfConfig",
    "OspfNetwork",
    "StaticRoute",
    "PduScenario",
    "PduItem",
    "TopologyNote",
    "PktMetadata",
    "WirelessConfig",
    "PktSecurityError",
    "PktFileSizeExceededError",
    "PktDecompressionLimitError",
    "PktXmlLimitError",
]
