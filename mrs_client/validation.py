"""Validation helpers for untrusted MRS inputs."""

from __future__ import annotations

from urllib.parse import urlsplit

_MAX_URI_LEN = 2048
_ALLOWED_SCHEMES = {"https"}


def validate_service_point_uri(value: str) -> str:
    """Validate a service_point URI under a strict safety policy.

    Policy:
    - absolute URI with scheme + host
    - https only
    - no userinfo credentials
    - no fragment
    - no control chars / whitespace
    - max length 2048
    """
    uri = value.strip()

    if not uri:
        raise ValueError("service_point must not be empty")
    if len(uri) > _MAX_URI_LEN:
        raise ValueError("service_point is too long")
    if any(ch.isspace() for ch in uri):
        raise ValueError("service_point must not contain whitespace")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in uri):
        raise ValueError("service_point contains control characters")

    parsed = urlsplit(uri)

    if not parsed.scheme:
        raise ValueError("service_point must include a URI scheme")
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError("service_point scheme must be https")
    if not parsed.netloc:
        raise ValueError("service_point must include a host")
    if parsed.username or parsed.password:
        raise ValueError("service_point must not include user credentials")
    if parsed.fragment:
        raise ValueError("service_point must not include fragments")
    if not parsed.hostname:
        raise ValueError("service_point host is invalid")

    return uri


def sanitize_service_point_uri(value: str | None) -> str | None:
    """Return validated URI or None if invalid/unset.

    Used when parsing untrusted server search results.
    """
    if value is None:
        return None
    try:
        return validate_service_point_uri(value)
    except ValueError:
        return None
