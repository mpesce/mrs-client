"""
MRS Client Library - Mixed Reality Service client for Python.

This library provides a client for the Mixed Reality Service (MRS) protocol,
which is like DNS for physical space: it maps coordinates to service URIs.
"""

from mrs_client.models import (
    Location,
    Sphere,
    Registration,
    Referral,
    SearchResult,
    ServerInfo,
    Identity,
)
from mrs_client.client import MRSClient
from mrs_client.exceptions import (
    MRSError,
    MRSConnectionError,
    MRSAuthError,
    MRSNotFoundError,
    MRSValidationError,
    MRSFederationError,
)

__version__ = "0.5.0"
__all__ = [
    # Main client
    "MRSClient",
    # Models
    "Location",
    "Sphere",
    "Registration",
    "Referral",
    "SearchResult",
    "ServerInfo",
    "Identity",
    # Exceptions
    "MRSError",
    "MRSConnectionError",
    "MRSAuthError",
    "MRSNotFoundError",
    "MRSValidationError",
    "MRSFederationError",
]
