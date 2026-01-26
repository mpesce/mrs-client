"""Main MRS client class."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

from mrs_client.auth import AuthManager
from mrs_client.config import Config, get_config_dir
from mrs_client.exceptions import (
    MRSAuthError,
    MRSConnectionError,
    MRSNotFoundError,
    MRSValidationError,
)
from mrs_client.http import HTTPClient, SyncHTTPClient
from mrs_client.models import (
    Identity,
    Location,
    Registration,
    SearchResult,
    ServerInfo,
    Sphere,
)
from mrs_client.search import SearchEngine, SyncSearchEngine


class MRSClient:
    """Main entry point for MRS operations.

    Provides both async and sync interfaces for all MRS operations.
    """

    def __init__(
        self,
        default_server: str | None = None,
        identity: str | None = None,
        config_dir: Path | None = None,
        max_referral_depth: int | None = None,
        timeout: float | None = None,
        verbose: bool = False,
        verbose_callback: Callable[[str], None] | None = None,
        test_mode: bool = False,
    ):
        """Initialize MRS client.

        Args:
            default_server: Server to query when none specified.
                          Overrides config file.
            identity: MRS identity (user@domain) for authenticated operations.
                     If not specified, uses configured identity.
            config_dir: Directory for keys and config. Uses platform default if None.
            max_referral_depth: Maximum referral chain length to follow.
            timeout: HTTP request timeout in seconds.
            verbose: Enable verbose HTTP logging.
            verbose_callback: Function to call with verbose messages.
            test_mode: Enable test mode (uses mock server).
        """
        self.config_dir = config_dir or get_config_dir()
        self._config = Config.load(self.config_dir)

        # Apply overrides
        if default_server:
            self._config.default_server = default_server
        if max_referral_depth is not None:
            self._config.max_referral_depth = max_referral_depth
        if timeout is not None:
            self._config.timeout_seconds = timeout
        if test_mode:
            self._config.test_mode = True

        self.verbose = verbose
        self._verbose_callback = verbose_callback

        # Initialize components
        self._auth = AuthManager(self.config_dir)

        # Set identity if specified
        self._identity_override = identity

        # HTTP clients (lazy initialized)
        self._async_http: HTTPClient | None = None
        self._sync_http: SyncHTTPClient | None = None
        self._async_search: SearchEngine | None = None
        self._sync_search: SyncSearchEngine | None = None

    def _get_async_http(self) -> HTTPClient:
        """Get or create async HTTP client."""
        if self._async_http is None:
            self._async_http = HTTPClient(
                timeout=self._config.timeout_seconds,
                verbose=self.verbose,
                verbose_callback=self._verbose_callback,
            )
        return self._async_http

    def _get_sync_http(self) -> SyncHTTPClient:
        """Get or create sync HTTP client."""
        if self._sync_http is None:
            self._sync_http = SyncHTTPClient(
                timeout=self._config.timeout_seconds,
                verbose=self.verbose,
                verbose_callback=self._verbose_callback,
            )
        return self._sync_http

    def _get_async_search(self) -> SearchEngine:
        """Get or create async search engine."""
        if self._async_search is None:
            self._async_search = SearchEngine(
                http_client=self._get_async_http(),
                max_depth=self._config.max_referral_depth,
                max_servers=self._config.max_servers,
                verbose_callback=self._verbose_callback if self.verbose else None,
            )
        return self._async_search

    def _get_sync_search(self) -> SyncSearchEngine:
        """Get or create sync search engine."""
        if self._sync_search is None:
            self._sync_search = SyncSearchEngine(
                http_client=self._get_sync_http(),
                max_depth=self._config.max_referral_depth,
                max_servers=self._config.max_servers,
                verbose_callback=self._verbose_callback if self.verbose else None,
            )
        return self._sync_search

    def _get_server(self, server: str | None = None) -> str:
        """Get effective server URL."""
        return self._config.get_effective_server(server)

    def _get_auth_headers(self, server: str) -> dict[str, str]:
        """Get authentication headers for a server."""
        return self._auth.get_auth_headers(server)

    # ============================================================
    # Async API
    # ============================================================

    async def search(
        self,
        lat: float,
        lon: float,
        ele: float = 0.0,
        range_meters: float = 0.0,
        servers: list[str] | None = None,
    ) -> SearchResult:
        """Search for registrations at a location.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            ele: Elevation in meters (default: 0)
            range_meters: Search radius in meters (default: 0 for exact point)
            servers: Servers to query. Uses default server if None.

        Returns:
            SearchResult with registrations found
        """
        location = Location(lat=lat, lon=lon, ele=ele)

        if servers is None:
            servers = [self._get_server()]

        search_engine = self._get_async_search()
        return await search_engine.search(
            location=location,
            range_meters=range_meters,
            initial_servers=servers,
        )

    async def register(
        self,
        lat: float,
        lon: float,
        radius: float,
        ele: float = 0.0,
        service_point: str | None = None,
        foad: bool = False,
        server: str | None = None,
    ) -> Registration:
        """Register a space.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius: Radius in meters
            ele: Center elevation (default: 0)
            service_point: Service URI (required unless foad=True)
            foad: If True, register as "no services" space
            server: Server to register with (uses default if None)

        Returns:
            Created Registration
        """
        if not foad and not service_point:
            raise MRSValidationError(
                "service_point is required when foad is False"
            )

        space = Sphere(center=Location(lat=lat, lon=lon, ele=ele), radius=radius)
        server_url = self._get_server(server)
        http = self._get_async_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(
                f"No authentication configured for {server_url}. "
                "Run 'mrs identity login' first."
            )

        payload: dict[str, Any] = {
            "space": space.to_dict(),
            "foad": foad,
        }
        if service_point:
            payload["service_point"] = service_point

        url = f"{server_url}/register"
        response = await http.post(url, json_data=payload, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed. Check your token or identity.")
        if response.status_code == 403:
            raise MRSAuthError("Not authorized to register at this server.")
        if response.status_code not in (200, 201):
            error_msg = "Unknown error"
            if response.json_data:
                error_msg = response.json_data.get("message", str(response.json_data))
            raise MRSValidationError(f"Registration failed: {error_msg}")

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return Registration.from_dict(response.json_data["registration"])

    async def release(
        self,
        registration_id: str,
        server: str | None = None,
    ) -> bool:
        """Release (delete) a registration.

        Args:
            registration_id: ID of registration to release
            server: Server to release from (uses default if None)

        Returns:
            True if released successfully
        """
        server_url = self._get_server(server)
        http = self._get_async_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/release"
        response = await http.post(
            url, json_data={"id": registration_id}, headers=headers
        )

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed.")
        if response.status_code == 403:
            raise MRSAuthError("Not authorized to release this registration.")
        if response.status_code == 404:
            raise MRSNotFoundError(f"Registration {registration_id} not found")
        if response.status_code != 200:
            raise MRSConnectionError(f"Release failed: {response.status_code}")

        return True

    async def list_registrations(
        self,
        server: str | None = None,
    ) -> list[Registration]:
        """List all registrations owned by current identity.

        Args:
            server: Server to list from (uses default if None)

        Returns:
            List of registrations
        """
        server_url = self._get_server(server)
        http = self._get_async_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/registrations"
        response = await http.get(url, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed.")
        if response.status_code != 200:
            raise MRSConnectionError(f"List failed: {response.status_code}")

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return [
            Registration.from_dict(r)
            for r in response.json_data.get("registrations", [])
        ]

    async def get_server_info(
        self,
        server: str | None = None,
    ) -> ServerInfo:
        """Get server metadata.

        Args:
            server: Server to query (uses default if None)

        Returns:
            ServerInfo with server details
        """
        server_url = self._get_server(server)
        http = self._get_async_http()

        url = f"{server_url}/.well-known/mrs"
        response = await http.get(url)

        if response.status_code != 200:
            raise MRSConnectionError(
                f"Failed to get server info: {response.status_code}"
            )

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return ServerInfo.from_dict(response.json_data, server_url)

    async def verify_auth(
        self,
        server: str | None = None,
    ) -> dict[str, Any]:
        """Verify authentication with a server.

        Args:
            server: Server to verify with (uses default if None)

        Returns:
            Dict with user info if authenticated
        """
        server_url = self._get_server(server)
        http = self._get_async_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/auth/me"
        response = await http.get(url, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed - token may be expired.")
        if response.status_code != 200:
            raise MRSConnectionError(f"Verification failed: {response.status_code}")

        return response.json_data or {}

    async def close(self) -> None:
        """Close HTTP clients."""
        if self._async_http:
            await self._async_http.close()

    async def __aenter__(self) -> "MRSClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ============================================================
    # Sync API
    # ============================================================

    def search_sync(
        self,
        lat: float,
        lon: float,
        ele: float = 0.0,
        range_meters: float = 0.0,
        servers: list[str] | None = None,
    ) -> SearchResult:
        """Search for registrations at a location (synchronous).

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            ele: Elevation in meters (default: 0)
            range_meters: Search radius in meters (default: 0 for exact point)
            servers: Servers to query. Uses default server if None.

        Returns:
            SearchResult with registrations found
        """
        location = Location(lat=lat, lon=lon, ele=ele)

        if servers is None:
            servers = [self._get_server()]

        search_engine = self._get_sync_search()
        return search_engine.search(
            location=location,
            range_meters=range_meters,
            initial_servers=servers,
        )

    def register_sync(
        self,
        lat: float,
        lon: float,
        radius: float,
        ele: float = 0.0,
        service_point: str | None = None,
        foad: bool = False,
        server: str | None = None,
    ) -> Registration:
        """Register a space (synchronous)."""
        if not foad and not service_point:
            raise MRSValidationError(
                "service_point is required when foad is False"
            )

        space = Sphere(center=Location(lat=lat, lon=lon, ele=ele), radius=radius)
        server_url = self._get_server(server)
        http = self._get_sync_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(
                f"No authentication configured for {server_url}. "
                "Run 'mrs identity login' first."
            )

        payload: dict[str, Any] = {
            "space": space.to_dict(),
            "foad": foad,
        }
        if service_point:
            payload["service_point"] = service_point

        url = f"{server_url}/register"
        response = http.post(url, json_data=payload, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed. Check your token or identity.")
        if response.status_code == 403:
            raise MRSAuthError("Not authorized to register at this server.")
        if response.status_code not in (200, 201):
            error_msg = "Unknown error"
            if response.json_data:
                error_msg = response.json_data.get("message", str(response.json_data))
            raise MRSValidationError(f"Registration failed: {error_msg}")

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return Registration.from_dict(response.json_data["registration"])

    def release_sync(
        self,
        registration_id: str,
        server: str | None = None,
    ) -> bool:
        """Release (delete) a registration (synchronous)."""
        server_url = self._get_server(server)
        http = self._get_sync_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/release"
        response = http.post(url, json_data={"id": registration_id}, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed.")
        if response.status_code == 403:
            raise MRSAuthError("Not authorized to release this registration.")
        if response.status_code == 404:
            raise MRSNotFoundError(f"Registration {registration_id} not found")
        if response.status_code != 200:
            raise MRSConnectionError(f"Release failed: {response.status_code}")

        return True

    def list_registrations_sync(
        self,
        server: str | None = None,
    ) -> list[Registration]:
        """List all registrations owned by current identity (synchronous)."""
        server_url = self._get_server(server)
        http = self._get_sync_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/registrations"
        response = http.get(url, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed.")
        if response.status_code != 200:
            raise MRSConnectionError(f"List failed: {response.status_code}")

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return [
            Registration.from_dict(r)
            for r in response.json_data.get("registrations", [])
        ]

    def get_server_info_sync(
        self,
        server: str | None = None,
    ) -> ServerInfo:
        """Get server metadata (synchronous)."""
        server_url = self._get_server(server)
        http = self._get_sync_http()

        url = f"{server_url}/.well-known/mrs"
        response = http.get(url)

        if response.status_code != 200:
            raise MRSConnectionError(
                f"Failed to get server info: {response.status_code}"
            )

        if response.json_data is None:
            raise MRSConnectionError("Server returned non-JSON response")

        return ServerInfo.from_dict(response.json_data, server_url)

    def verify_auth_sync(
        self,
        server: str | None = None,
    ) -> dict[str, Any]:
        """Verify authentication with a server (synchronous)."""
        server_url = self._get_server(server)
        http = self._get_sync_http()

        headers = self._get_auth_headers(server_url)
        if not headers:
            raise MRSAuthError(f"No authentication configured for {server_url}")

        url = f"{server_url}/auth/me"
        response = http.get(url, headers=headers)

        if response.status_code == 401:
            raise MRSAuthError("Authentication failed - token may be expired.")
        if response.status_code != 200:
            raise MRSConnectionError(f"Verification failed: {response.status_code}")

        return response.json_data or {}

    def close_sync(self) -> None:
        """Close sync HTTP client."""
        if self._sync_http:
            self._sync_http.close()

    # ============================================================
    # Identity operations (always synchronous)
    # ============================================================

    def get_identity(self) -> Identity | None:
        """Get current identity."""
        return self._auth.get_identity()

    def create_identity(self, username: str, domain: str) -> Identity:
        """Create new identity with generated keys.

        Args:
            username: Username part of identity
            domain: Domain part of identity (usually server domain)

        Returns:
            New Identity
        """
        return self._auth.generate_identity(username, domain)

    def store_token(
        self, server: str, token: str, expires_at: str | None = None
    ) -> None:
        """Store bearer token for a server.

        Args:
            server: Server URL
            token: Bearer token
            expires_at: Optional expiration timestamp (ISO format)
        """
        self._auth.store_bearer_token(server, token, expires_at)

    def get_token(self, server: str | None = None) -> str | None:
        """Get bearer token for a server.

        Args:
            server: Server URL (uses default if None)

        Returns:
            Token or None if not configured
        """
        server_url = self._get_server(server)
        return self._auth.get_bearer_token(server_url)

    def remove_token(self, server: str | None = None) -> None:
        """Remove bearer token for a server.

        Args:
            server: Server URL (uses default if None)
        """
        server_url = self._get_server(server)
        self._auth.remove_bearer_token(server_url)

    def export_public_key(self) -> dict[str, Any]:
        """Export public key in MRS format."""
        return self._auth.export_public_key()

    @property
    def default_server(self) -> str:
        """Get current default server."""
        return self._config.default_server

    @property
    def config(self) -> Config:
        """Get configuration."""
        return self._config
