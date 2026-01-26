"""HTTP client wrapper with verbose logging support."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from mrs_client.exceptions import MRSConnectionError


@dataclass
class HTTPResponse:
    """Wrapper for HTTP response with timing info."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    json_data: Any | None
    elapsed_ms: float


class HTTPClient:
    """HTTP client with verbose logging support."""

    def __init__(
        self,
        timeout: float = 30.0,
        verbose: bool = False,
        verbose_callback: Callable[[str], None] | None = None,
    ):
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
            verbose_callback: Function to call with verbose log messages.
                            If None and verbose=True, prints to stderr.
        """
        self.timeout = timeout
        self.verbose = verbose
        self._verbose_callback = verbose_callback
        self._client: httpx.AsyncClient | None = None

    def _log(self, message: str) -> None:
        """Log a verbose message."""
        if not self.verbose:
            return
        if self._verbose_callback:
            self._verbose_callback(message)
        else:
            import sys

            print(message, file=sys.stderr)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: Any | None = None,
    ) -> HTTPResponse:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional request headers
            json_data: Optional JSON body

        Returns:
            HTTPResponse with status, headers, body, and timing

        Raises:
            MRSConnectionError: If connection fails
        """
        client = await self._get_client()
        headers = headers or {}

        # Log request
        self._log(f"[HTTP] {method} {url}")
        if headers:
            for key, value in headers.items():
                # Mask authorization tokens
                if key.lower() == "authorization":
                    if value.startswith("Bearer "):
                        value = f"Bearer {value[7:15]}..."
                self._log(f"[HTTP] > {key}: {value}")
        if json_data:
            import json

            body_str = json.dumps(json_data)
            if len(body_str) > 200:
                body_str = body_str[:200] + "..."
            self._log(f"[HTTP] > Body: {body_str}")

        start_time = time.monotonic()

        try:
            if json_data is not None:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                )
            else:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Log response
            self._log(f"[HTTP] < {response.status_code} ({elapsed_ms:.0f}ms)")
            for key, value in response.headers.items():
                if key.lower() in ("content-type", "content-length"):
                    self._log(f"[HTTP] < {key}: {value}")

            # Parse JSON if applicable
            json_result = None
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    json_result = response.json()
                    body_str = str(json_result)
                    if len(body_str) > 300:
                        body_str = body_str[:300] + "..."
                    self._log(f"[HTTP] < Body: {body_str}")
                except Exception:
                    pass

            return HTTPResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.content,
                json_data=json_result,
                elapsed_ms=elapsed_ms,
            )

        except httpx.ConnectError as e:
            raise MRSConnectionError(f"Failed to connect to {url}: {e}") from e
        except httpx.TimeoutException as e:
            raise MRSConnectionError(f"Request to {url} timed out: {e}") from e
        except httpx.HTTPError as e:
            raise MRSConnectionError(f"HTTP error for {url}: {e}") from e

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        return await self.request("GET", url, headers=headers)

    async def post(
        self,
        url: str,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """Make a POST request."""
        return await self.request("POST", url, headers=headers, json_data=json_data)


class SyncHTTPClient:
    """Synchronous wrapper around HTTPClient."""

    def __init__(
        self,
        timeout: float = 30.0,
        verbose: bool = False,
        verbose_callback: Callable[[str], None] | None = None,
    ):
        self.timeout = timeout
        self.verbose = verbose
        self._verbose_callback = verbose_callback
        self._client: httpx.Client | None = None

    def _log(self, message: str) -> None:
        """Log a verbose message."""
        if not self.verbose:
            return
        if self._verbose_callback:
            self._verbose_callback(message)
        else:
            import sys

            print(message, file=sys.stderr)

    def _get_client(self) -> httpx.Client:
        """Get or create the sync HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: Any | None = None,
    ) -> HTTPResponse:
        """Make an HTTP request (synchronous)."""
        client = self._get_client()
        headers = headers or {}

        # Log request
        self._log(f"[HTTP] {method} {url}")
        if headers:
            for key, value in headers.items():
                if key.lower() == "authorization":
                    if value.startswith("Bearer "):
                        value = f"Bearer {value[7:15]}..."
                self._log(f"[HTTP] > {key}: {value}")
        if json_data:
            import json

            body_str = json.dumps(json_data)
            if len(body_str) > 200:
                body_str = body_str[:200] + "..."
            self._log(f"[HTTP] > Body: {body_str}")

        start_time = time.monotonic()

        try:
            if json_data is not None:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                )
            else:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Log response
            self._log(f"[HTTP] < {response.status_code} ({elapsed_ms:.0f}ms)")

            # Parse JSON if applicable
            json_result = None
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    json_result = response.json()
                    body_str = str(json_result)
                    if len(body_str) > 300:
                        body_str = body_str[:300] + "..."
                    self._log(f"[HTTP] < Body: {body_str}")
                except Exception:
                    pass

            return HTTPResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.content,
                json_data=json_result,
                elapsed_ms=elapsed_ms,
            )

        except httpx.ConnectError as e:
            raise MRSConnectionError(f"Failed to connect to {url}: {e}") from e
        except httpx.TimeoutException as e:
            raise MRSConnectionError(f"Request to {url} timed out: {e}") from e
        except httpx.HTTPError as e:
            raise MRSConnectionError(f"HTTP error for {url}: {e}") from e

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        return self.request("GET", url, headers=headers)

    def post(
        self,
        url: str,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        """Make a POST request."""
        return self.request("POST", url, headers=headers, json_data=json_data)
