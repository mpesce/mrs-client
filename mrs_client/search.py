"""Search engine with federated referral following."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from mrs_client.exceptions import MRSFederationError
from mrs_client.geo import haversine_distance
from mrs_client.http import HTTPClient, SyncHTTPClient
from mrs_client.models import Location, Referral, Registration, SearchResult, Sphere

logger = logging.getLogger(__name__)


class SearchEngine:
    """Handles federated search with referral following."""

    def __init__(
        self,
        http_client: HTTPClient,
        max_depth: int = 5,
        max_servers: int = 20,
        verbose_callback: Callable[[str], None] | None = None,
    ):
        """Initialize search engine.

        Args:
            http_client: HTTP client for making requests
            max_depth: Maximum referral chain length to follow
            max_servers: Maximum number of servers to query
            verbose_callback: Optional callback for verbose logging
        """
        self.http = http_client
        self.max_depth = max_depth
        self.max_servers = max_servers
        self._verbose_callback = verbose_callback

    def _log(self, message: str) -> None:
        """Log a message."""
        if self._verbose_callback:
            self._verbose_callback(message)
        logger.debug(message)

    async def search(
        self,
        location: Location,
        range_meters: float,
        initial_servers: list[str],
    ) -> SearchResult:
        """Execute federated search.

        1. Query initial servers
        2. Collect results and referrals
        3. Follow referrals up to max_depth
        4. Deduplicate results by registration ID
        5. Sort by volume (smallest first), then distance
        6. Return aggregated results

        Args:
            location: Center point for search
            range_meters: Search radius in meters (0 for exact point)
            initial_servers: Servers to start search from

        Returns:
            SearchResult with deduplicated, sorted results
        """
        visited: set[str] = set()
        all_results: dict[str, Registration] = {}  # id -> registration
        queue: list[tuple[str, int]] = [
            (s, 0) for s in initial_servers
        ]  # (server, depth)

        start_time = time.monotonic()

        while queue and len(visited) < self.max_servers:
            server, depth = queue.pop(0)

            # Normalize server URL
            server = server.rstrip("/")

            if server in visited:
                continue
            if depth > self.max_depth:
                self._log(f"Skipping {server} - max depth {self.max_depth} exceeded")
                continue

            visited.add(server)

            try:
                self._log(f"Querying {server} (depth {depth})...")
                response = await self._query_server(server, location, range_meters)

                # Collect results
                for reg in response["results"]:
                    reg_id = reg["id"]
                    registration = Registration.from_dict(reg)

                    # Calculate distance if not provided
                    if registration.distance is None:
                        registration.distance = haversine_distance(
                            location, registration.space.center
                        )

                    if reg_id not in all_results:
                        all_results[reg_id] = registration
                    elif (
                        registration.distance is not None
                        and registration.distance
                        < (all_results[reg_id].distance or float("inf"))
                    ):
                        # Keep the one with smaller distance if duplicate
                        all_results[reg_id] = registration

                # Queue referrals
                for referral_data in response.get("referrals", []):
                    referral = Referral.from_dict(referral_data)
                    referral_server = referral.server.rstrip("/")
                    if referral_server not in visited:
                        hint = f" ({referral.hint})" if referral.hint else ""
                        self._log(f"Following referral to {referral_server}{hint}")
                        queue.append((referral_server, depth + 1))

            except Exception as e:
                self._log(f"Failed to query {server}: {e}")
                logger.warning(f"Failed to query {server}: {e}")
                continue

        # Sort results
        sorted_results = self._sort_results(list(all_results.values()))

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return SearchResult(
            results=sorted_results,
            servers_queried=list(visited),
            referrals_followed=len(visited) - len(initial_servers),
            total_time_ms=elapsed_ms,
        )

    async def _query_server(
        self, server: str, location: Location, range_meters: float
    ) -> dict[str, Any]:
        """Query a single server.

        Args:
            server: Server URL
            location: Search location
            range_meters: Search range

        Returns:
            Server response dict with results and referrals
        """
        url = f"{server}/search"
        payload = {
            "location": location.to_dict(),
            "range": range_meters,
        }

        response = await self.http.post(url, json_data=payload)

        if response.status_code != 200:
            raise MRSFederationError(
                f"Server {server} returned {response.status_code}: "
                f"{response.json_data or response.body.decode()}"
            )

        if response.json_data is None:
            raise MRSFederationError(f"Server {server} returned non-JSON response")

        return response.json_data

    def _sort_results(self, results: list[Registration]) -> list[Registration]:
        """Sort by volume (smallest first), then by distance."""

        def sort_key(r: Registration) -> tuple[float, float]:
            volume = self._compute_volume(r.space)
            distance = r.distance if r.distance is not None else float("inf")
            return (volume, distance)

        return sorted(results, key=sort_key)

    def _compute_volume(self, space: Sphere) -> float:
        """Compute volume for sorting."""
        return space.volume()


class SyncSearchEngine:
    """Synchronous search engine with referral following."""

    def __init__(
        self,
        http_client: SyncHTTPClient,
        max_depth: int = 5,
        max_servers: int = 20,
        verbose_callback: Callable[[str], None] | None = None,
    ):
        self.http = http_client
        self.max_depth = max_depth
        self.max_servers = max_servers
        self._verbose_callback = verbose_callback

    def _log(self, message: str) -> None:
        if self._verbose_callback:
            self._verbose_callback(message)
        logger.debug(message)

    def search(
        self,
        location: Location,
        range_meters: float,
        initial_servers: list[str],
    ) -> SearchResult:
        """Execute federated search (synchronous version)."""
        visited: set[str] = set()
        all_results: dict[str, Registration] = {}
        queue: list[tuple[str, int]] = [(s, 0) for s in initial_servers]

        start_time = time.monotonic()

        while queue and len(visited) < self.max_servers:
            server, depth = queue.pop(0)
            server = server.rstrip("/")

            if server in visited:
                continue
            if depth > self.max_depth:
                self._log(f"Skipping {server} - max depth {self.max_depth} exceeded")
                continue

            visited.add(server)

            try:
                self._log(f"Querying {server} (depth {depth})...")
                response = self._query_server(server, location, range_meters)

                for reg in response["results"]:
                    reg_id = reg["id"]
                    registration = Registration.from_dict(reg)

                    if registration.distance is None:
                        registration.distance = haversine_distance(
                            location, registration.space.center
                        )

                    if reg_id not in all_results:
                        all_results[reg_id] = registration
                    elif (
                        registration.distance is not None
                        and registration.distance
                        < (all_results[reg_id].distance or float("inf"))
                    ):
                        all_results[reg_id] = registration

                for referral_data in response.get("referrals", []):
                    referral = Referral.from_dict(referral_data)
                    referral_server = referral.server.rstrip("/")
                    if referral_server not in visited:
                        hint = f" ({referral.hint})" if referral.hint else ""
                        self._log(f"Following referral to {referral_server}{hint}")
                        queue.append((referral_server, depth + 1))

            except Exception as e:
                self._log(f"Failed to query {server}: {e}")
                logger.warning(f"Failed to query {server}: {e}")
                continue

        sorted_results = self._sort_results(list(all_results.values()))
        elapsed_ms = (time.monotonic() - start_time) * 1000

        return SearchResult(
            results=sorted_results,
            servers_queried=list(visited),
            referrals_followed=len(visited) - len(initial_servers),
            total_time_ms=elapsed_ms,
        )

    def _query_server(
        self, server: str, location: Location, range_meters: float
    ) -> dict[str, Any]:
        url = f"{server}/search"
        payload = {
            "location": location.to_dict(),
            "range": range_meters,
        }

        response = self.http.post(url, json_data=payload)

        if response.status_code != 200:
            raise MRSFederationError(
                f"Server {server} returned {response.status_code}: "
                f"{response.json_data or response.body.decode()}"
            )

        if response.json_data is None:
            raise MRSFederationError(f"Server {server} returned non-JSON response")

        return response.json_data

    def _sort_results(self, results: list[Registration]) -> list[Registration]:
        def sort_key(r: Registration) -> tuple[float, float]:
            volume = r.space.volume()
            distance = r.distance if r.distance is not None else float("inf")
            return (volume, distance)

        return sorted(results, key=sort_key)
