"""Mock MRS server for testing without network access."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mrs_client.geo import (
    haversine_distance,
    search_sphere_intersects_registration,
)
from mrs_client.models import Location, Registration, Sphere


@dataclass
class MockUser:
    """Mock user for testing."""

    identity: str
    token: str


@dataclass
class MockServer:
    """In-memory MRS server for testing.

    This provides a complete MRS server implementation that runs locally,
    allowing testing without network access or a real server.
    """

    server_url: str = "http://localhost:8000"
    operator: str = "test@localhost"

    # Storage
    registrations: dict[str, dict[str, Any]] = field(default_factory=dict)
    users: dict[str, MockUser] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)  # token -> identity
    peers: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Create a default test user
        self.add_user("test@localhost", "test-token-12345")

    def add_user(self, identity: str, token: str) -> MockUser:
        """Add a user with a bearer token."""
        user = MockUser(identity=identity, token=token)
        self.users[identity] = user
        self.tokens[token] = identity
        return user

    def add_peer(self, server_url: str, hint: str | None = None) -> None:
        """Add a peer server."""
        peer: dict[str, str] = {"server": server_url}
        if hint:
            peer["hint"] = hint
        self.peers.append(peer)

    def authenticate(self, auth_header: str | None) -> str | None:
        """Authenticate a request, return identity or None."""
        if not auth_header:
            return None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self.tokens.get(token)
        return None

    def handle_request(
        self, method: str, path: str, body: dict[str, Any] | None, headers: dict[str, str]
    ) -> tuple[int, dict[str, Any]]:
        """Handle an HTTP request and return (status_code, response_body).

        This simulates the MRS server API.
        """
        # Route the request
        if path == "/.well-known/mrs" and method == "GET":
            return self._handle_wellknown()
        elif path == "/search" and method == "POST":
            return self._handle_search(body or {})
        elif path == "/register" and method == "POST":
            identity = self.authenticate(headers.get("Authorization"))
            if not identity:
                return 401, {"status": "error", "message": "Unauthorized"}
            return self._handle_register(body or {}, identity)
        elif path == "/release" and method == "POST":
            identity = self.authenticate(headers.get("Authorization"))
            if not identity:
                return 401, {"status": "error", "message": "Unauthorized"}
            return self._handle_release(body or {}, identity)
        elif path == "/registrations" and method == "GET":
            identity = self.authenticate(headers.get("Authorization"))
            if not identity:
                return 401, {"status": "error", "message": "Unauthorized"}
            return self._handle_list(identity)
        elif path == "/auth/me" and method == "GET":
            identity = self.authenticate(headers.get("Authorization"))
            if not identity:
                return 401, {"status": "error", "message": "Unauthorized"}
            return self._handle_auth_me(identity)
        else:
            return 404, {"status": "error", "message": "Not found"}

    def _handle_wellknown(self) -> tuple[int, dict[str, Any]]:
        """Handle GET /.well-known/mrs"""
        return 200, {
            "mrs_version": "0.5.0",
            "server": self.server_url,
            "operator": self.operator,
            "authoritative_regions": [],
            "known_peers": self.peers,
            "capabilities": {
                "geometry_types": ["sphere"],
                "max_radius": 1000000,
            },
        }

    def _handle_search(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Handle POST /search"""
        location_data = body.get("location", {})
        range_meters = body.get("range", 0.0)

        try:
            location = Location(
                lat=location_data.get("lat", 0),
                lon=location_data.get("lon", 0),
                ele=location_data.get("ele", 0),
            )
        except ValueError as e:
            return 400, {"status": "error", "message": str(e)}

        results = []
        for reg_id, reg_data in self.registrations.items():
            space_data = reg_data["space"]
            if space_data["type"] == "sphere":
                sphere = Sphere(
                    center=Location(
                        lat=space_data["center"]["lat"],
                        lon=space_data["center"]["lon"],
                        ele=space_data["center"].get("ele", 0),
                    ),
                    radius=space_data["radius"],
                )

                if search_sphere_intersects_registration(location, range_meters, sphere):
                    distance = haversine_distance(location, sphere.center)
                    result = {
                        **reg_data,
                        "id": reg_id,
                        "distance": distance,
                    }
                    results.append(result)

        # Sort by volume (smallest first), then distance
        def sort_key(r: dict[str, Any]) -> tuple[float, float]:
            space = r["space"]
            if space["type"] == "sphere":
                volume = (4 / 3) * 3.14159 * (space["radius"] ** 3)
            else:
                volume = float("inf")
            return (volume, r.get("distance", float("inf")))

        results.sort(key=sort_key)

        return 200, {
            "status": "ok",
            "results": results,
            "referrals": self.peers,
        }

    def _handle_register(
        self, body: dict[str, Any], identity: str
    ) -> tuple[int, dict[str, Any]]:
        """Handle POST /register"""
        space = body.get("space")
        service_point = body.get("service_point")
        foad = body.get("foad", False)

        if not space:
            return 400, {"status": "error", "message": "space is required"}

        if space.get("type") != "sphere":
            return 400, {"status": "error", "message": "Only sphere geometry supported"}

        center = space.get("center", {})
        radius = space.get("radius")

        if radius is None:
            return 400, {"status": "error", "message": "radius is required"}

        if radius <= 0 or radius > 1_000_000:
            return 400, {
                "status": "error",
                "message": "radius must be between 0 and 1,000,000",
            }

        if not foad and not service_point:
            return 400, {
                "status": "error",
                "message": "service_point required when foad is false",
            }

        # Generate registration ID
        reg_id = f"reg_{secrets.token_urlsafe(9)}"
        now = datetime.now(timezone.utc).isoformat()

        registration = {
            "space": {
                "type": "sphere",
                "center": {
                    "lat": center.get("lat", 0),
                    "lon": center.get("lon", 0),
                    "ele": center.get("ele", 0),
                },
                "radius": radius,
            },
            "foad": foad,
            "owner": identity,
            "created": now,
            "updated": now,
        }
        if service_point:
            registration["service_point"] = service_point

        self.registrations[reg_id] = registration

        return 201, {
            "status": "registered",
            "registration": {
                "id": reg_id,
                **registration,
            },
        }

    def _handle_release(
        self, body: dict[str, Any], identity: str
    ) -> tuple[int, dict[str, Any]]:
        """Handle POST /release"""
        reg_id = body.get("id")
        if not reg_id:
            return 400, {"status": "error", "message": "id is required"}

        if reg_id not in self.registrations:
            return 404, {"status": "error", "message": "Registration not found"}

        if self.registrations[reg_id]["owner"] != identity:
            return 403, {"status": "error", "message": "Not authorized"}

        del self.registrations[reg_id]
        return 200, {"status": "released", "id": reg_id}

    def _handle_list(self, identity: str) -> tuple[int, dict[str, Any]]:
        """Handle GET /registrations"""
        results = []
        for reg_id, reg_data in self.registrations.items():
            if reg_data["owner"] == identity:
                results.append({"id": reg_id, **reg_data})

        return 200, {
            "registrations": results,
            "total": len(results),
            "limit": 100,
            "offset": 0,
        }

    def _handle_auth_me(self, identity: str) -> tuple[int, dict[str, Any]]:
        """Handle GET /auth/me"""
        reg_count = sum(
            1 for r in self.registrations.values() if r["owner"] == identity
        )
        return 200, {
            "id": identity,
            "created_at": "2026-01-01T00:00:00Z",
            "can_register": True,
            "registration_count": reg_count,
        }

    # Convenience methods for adding test data
    def add_registration(
        self,
        lat: float,
        lon: float,
        radius: float,
        service_point: str | None = None,
        foad: bool = False,
        owner: str = "test@localhost",
        ele: float = 0.0,
    ) -> str:
        """Add a registration directly (for test setup).

        Returns the registration ID.
        """
        reg_id = f"reg_{secrets.token_urlsafe(9)}"
        now = datetime.now(timezone.utc).isoformat()

        registration: dict[str, Any] = {
            "space": {
                "type": "sphere",
                "center": {"lat": lat, "lon": lon, "ele": ele},
                "radius": radius,
            },
            "foad": foad,
            "owner": owner,
            "created": now,
            "updated": now,
        }
        if service_point:
            registration["service_point"] = service_point

        self.registrations[reg_id] = registration
        return reg_id


# Global mock server instance for testing
_mock_server: MockServer | None = None


def get_mock_server() -> MockServer:
    """Get the global mock server instance."""
    global _mock_server
    if _mock_server is None:
        _mock_server = MockServer()
    return _mock_server


def reset_mock_server() -> MockServer:
    """Reset the global mock server (clears all data)."""
    global _mock_server
    _mock_server = MockServer()
    return _mock_server
