"""Exception classes for MRS client."""


class MRSError(Exception):
    """Base exception for MRS client errors."""

    pass


class MRSConnectionError(MRSError):
    """Failed to connect to server."""

    pass


class MRSAuthError(MRSError):
    """Authentication failed."""

    pass


class MRSNotFoundError(MRSError):
    """Resource not found."""

    pass


class MRSValidationError(MRSError):
    """Invalid input data."""

    pass


class MRSFederationError(MRSError):
    """Federation/referral following failed."""

    pass
